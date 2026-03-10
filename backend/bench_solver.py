"""Benchmark: time the solver on various scramble lengths."""
import sys, time
sys.path.insert(0, '.')
import cuda_solver

def apply_move(state, move):
    state = list(state)
    face = move[0]
    mod = move[1] if len(move) > 1 else ''
    turns = 2 if mod == '2' else (3 if mod == "'" else 1)
    def cycle(a, b, c, d):
        state[a], state[b], state[c], state[d] = state[d], state[a], state[b], state[c]
    def rotate_face(b):
        cycle(b, b+2, b+8, b+6); cycle(b+1, b+5, b+7, b+3)
    for _ in range(turns):
        if face == 'U':
            rotate_face(0); cycle(18,36,45,9); cycle(19,37,46,10); cycle(20,38,47,11)
        elif face == 'D':
            rotate_face(27); cycle(24,15,51,42); cycle(25,16,52,43); cycle(26,17,53,44)
        elif face == 'F':
            rotate_face(18); cycle(6,9,29,44); cycle(7,12,28,41); cycle(8,15,27,38)
        elif face == 'B':
            rotate_face(45); cycle(2,36,33,17); cycle(1,39,34,14); cycle(0,42,35,11)
        elif face == 'L':
            rotate_face(36); cycle(0,18,27,53); cycle(3,21,30,50); cycle(6,24,33,47)
        elif face == 'R':
            rotate_face(9); cycle(8,45,35,26); cycle(5,48,32,23); cycle(2,51,29,20)
    return state

COLOR_MAP = "URFDLB"
solved = [i // 9 for i in range(54)]

def state_to_str(state):
    return ''.join(COLOR_MAP[c] for c in state)

def scramble_state(moves_str):
    state = list(solved)
    for m in moves_str.split():
        state = apply_move(state, m)
    return state_to_str(state)

# Test cases of increasing difficulty
tests = [
    "R U R' U'",                          # 4 moves
    "R U R' U' R U R' U'",                # 8 (may solve shorter)
    "F R U R' U' F'",                     # 6 moves (OLL)
    "R U2 R' U' R U' R'",                 # 7 moves
    "L F2 R' D B' L U2 F R D' L' B",     # 12 moves  
    "R U F D L B R' U' F' D' L' B'",     # 12 moves
]

print("Benchmarking solver...\n")
for scramble in tests:
    cube = scramble_state(scramble)
    t0 = time.perf_counter()
    solution = cuda_solver.solve(cube)
    dt = (time.perf_counter() - t0) * 1000
    moves = solution.split() if solution else []
    print(f"  Scramble: {scramble}")
    print(f"  Solution: {solution}  ({len(moves)} moves, {dt:.0f} ms)\n")
