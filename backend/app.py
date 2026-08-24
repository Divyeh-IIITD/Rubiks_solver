import os
import sys
import time
import random
import threading
import multiprocessing
import queue
from flask import Flask, request, jsonify
from flask_cors import CORS

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

app = Flask(__name__)
CORS(app)

CUDA_AVAILABLE = False
try:
    import cuda_solver
    CUDA_AVAILABLE = True
    print("[solver] CUDA solver loaded [OK]")
except ImportError:
    pass

KOCIEMBA_AVAILABLE = False
try:
    import kociemba
    KOCIEMBA_AVAILABLE = True
    print("[solver] kociemba loaded [OK]")
except ImportError:
    pass


def _cuda_persistent_worker(req_q, res_q):
    """Long-lived worker process that keeps PDB and GPU tables pre-warmed in memory."""
    try:
        import cuda_solver as cs
        if hasattr(cs, 'init'):
            cs.init()
        else:
            cs.solve("UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB")
    except Exception as e:
        print(f"[solver] Worker initialization error: {e}")

    while True:
        try:
            req = req_q.get()
            if req is None:
                break
            req_id, cube_string = req
            import cuda_solver as cs
            sol = cs.solve(cube_string)
            res_q.put((req_id, sol))
        except Exception as e:
            res_q.put((req_id, None))


class CudaWorkerManager:
    def __init__(self, timeout_sec=6.0):
        self.timeout_sec = timeout_sec
        self.proc = None
        self.req_q = None
        self.res_q = None
        self.lock = threading.Lock()

    def _start_worker(self):
        try:
            if self.proc is not None and self.proc.is_alive():
                self.proc.kill()
                self.proc.join(timeout=0.5)
        except Exception:
            pass
        self.req_q = multiprocessing.Queue()
        self.res_q = multiprocessing.Queue()
        self.proc = multiprocessing.Process(
            target=_cuda_persistent_worker,
            args=(self.req_q, self.res_q),
            daemon=True
        )
        self.proc.start()

    def solve(self, cube_string):
        if not CUDA_AVAILABLE:
            return None, None, False
        with self.lock:
            if self.proc is None or not self.proc.is_alive():
                self._start_worker()

            req_id = random.randint(1, 1000000)
            self.req_q.put((req_id, cube_string))

            t0 = time.perf_counter()
            while time.perf_counter() - t0 < self.timeout_sec:
                try:
                    res_id, sol = self.res_q.get(timeout=0.05)
                    if res_id == req_id:
                        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                        moves = sol.strip().split() if sol and sol.strip() else []
                        return moves, elapsed_ms, False
                except queue.Empty:
                    if not self.proc.is_alive():
                        self._start_worker()
                        return None, None, False

            # Timed out
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            print(f"[solver] CUDA timed out after {elapsed_ms} ms, falling back to Kociemba")
            self._start_worker()
            return None, elapsed_ms, True


cuda_mgr = CudaWorkerManager(timeout_sec=6.0)


def solve_both(cube_string):
    """Run both CUDA and Kociemba solvers, return primary result + comparison."""
    cuda_moves, cuda_ms, cuda_timed_out = cuda_mgr.solve(cube_string)

    kociemba_ms = None
    kociemba_moves = None
    if KOCIEMBA_AVAILABLE:
        t0 = time.perf_counter()
        sol = kociemba.solve(cube_string)
        kociemba_ms = round((time.perf_counter() - t0) * 1000, 2)
        kociemba_moves = sol.strip().split() if sol.strip() else []

    if cuda_moves is not None and not cuda_timed_out:
        primary_moves, primary_solver, primary_ms = cuda_moves, "CUDA", cuda_ms
    elif kociemba_moves is not None:
        primary_moves, primary_solver, primary_ms = kociemba_moves, "Kociemba (CPU)", kociemba_ms
    else:
        raise RuntimeError("No solver available. Run: pip install kociemba")

    return primary_moves, primary_solver, primary_ms, cuda_ms, kociemba_ms, \
           cuda_moves, kociemba_moves


ALL_MOVES = ["U", "U'", "U2", "D", "D'", "D2",
             "R", "R'", "R2", "L", "L'", "L2",
             "F", "F'", "F2", "B", "B'", "B2"]


def generate_scramble(length=12):
    scramble = []
    last_face = None
    for _ in range(length):
        candidates = [m for m in ALL_MOVES if m[0] != last_face]
        move = random.choice(candidates)
        scramble.append(move)
        last_face = move[0]
    return scramble


def apply_move(state, move):
    face = move[0]
    mod = move[1] if len(move) > 1 else ''
    turns = 2 if mod == '2' else (3 if mod == "'" else 1)

    def cycle(a, b, c, d):
        state[a], state[b], state[c], state[d] = state[d], state[a], state[b], state[c]
        
    def rotate_face(b):
        cycle(b, b+2, b+8, b+6)
        cycle(b+1, b+5, b+7, b+3)

    for _ in range(turns):
        if face == 'U':
            rotate_face(0)
            cycle(18, 36, 45, 9); cycle(19, 37, 46, 10); cycle(20, 38, 47, 11)
        elif face == 'D':
            rotate_face(27)
            cycle(24, 15, 51, 42); cycle(25, 16, 52, 43); cycle(26, 17, 53, 44)
        elif face == 'F':
            rotate_face(18)
            cycle(6, 9, 29, 44); cycle(7, 12, 28, 41); cycle(8, 15, 27, 38)
        elif face == 'B':
            rotate_face(45)
            cycle(2, 36, 33, 17); cycle(1, 39, 34, 14); cycle(0, 42, 35, 11)
        elif face == 'L':
            rotate_face(36)
            cycle(0, 18, 27, 53); cycle(3, 21, 30, 50); cycle(6, 24, 33, 47)
        elif face == 'R':
            rotate_face(9)
            cycle(8, 45, 35, 26); cycle(5, 48, 32, 23); cycle(2, 51, 29, 20)
    return state


def scramble_to_state(scramble_moves):
    solved = "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB"
    state = list(solved)
    for move in scramble_moves:
        apply_move(state, move)
    return ''.join(state)


@app.route('/solve', methods=['POST'])
def solve():
    data = request.get_json()
    cube_string = data.get('cube_string', '')
    if len(cube_string) != 54:
        return jsonify({'error': 'Invalid cube string. Must be 54 characters.'}), 400
    
    valid_chars = set('URFDLB')
    if not all(c in valid_chars for c in cube_string):
        return jsonify({'error': 'Invalid characters in cube string.'}), 400
        
    for c in valid_chars:
        if cube_string.count(c) != 9:
            return jsonify({'error': f'Color {c} does not appear exactly 9 times.'}), 400
            
    if cube_string == "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB":
        return jsonify({'solution': [], 'move_count': 0, 'solver': 'N/A', 'solve_time_ms': 0})
        
    try:
        moves, solver_name, elapsed_ms, cuda_ms, kociemba_ms, cuda_sol, kociemba_sol = solve_both(cube_string)
        result = {
            'solution': moves,
            'move_count': len(moves),
            'solver': solver_name,
            'solve_time_ms': elapsed_ms,
            'comparison': {
                'cuda_ms': cuda_ms,
                'kociemba_ms': kociemba_ms,
                'cuda_moves': len(cuda_sol) if cuda_sol else None,
                'kociemba_moves': len(kociemba_sol) if kociemba_sol else None,
                'cuda_solution': cuda_sol,
                'kociemba_solution': kociemba_sol,
            }
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Could not solve cube: {str(e)}'}), 400


@app.route('/scramble', methods=['GET'])
def scramble():
    length = int(request.args.get('length', 12))
    length = max(4, min(length, 30))
    moves = generate_scramble(length)
    cube_string = scramble_to_state(moves)
    return jsonify({'scramble_moves': moves, 'cube_string': cube_string})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'cuda_available': CUDA_AVAILABLE,
        'kociemba_available': KOCIEMBA_AVAILABLE,
        'solver': 'CUDA' if CUDA_AVAILABLE else ('Kociemba' if KOCIEMBA_AVAILABLE else 'none'),
    })


if __name__ == '__main__':
    multiprocessing.freeze_support()
    app.run(debug=True, port=5000)