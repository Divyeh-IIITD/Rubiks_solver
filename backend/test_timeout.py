import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
import time
import multiprocessing
from app import scramble_to_state, solve_both

if __name__ == '__main__':
    multiprocessing.freeze_support()
    # Hard 20-move scramble that triggers CUDA timeout
    cube = scramble_to_state(['R','U','F','D','L','B','R2','U2','F2','D2','L2','B2','R','U','F','D','L','B','R2','U2'])
    print("Cube:", cube)

    print("\n--- Testing CUDA solve_both with timeout & fallback ---")
    t0 = time.perf_counter()
    moves, solver_name, elapsed_ms, cuda_ms, kociemba_ms, cuda_count, kociemba_count = solve_both(cube)
    total_time = round((time.perf_counter() - t0) * 1000, 2)
    
    print(f"Primary Solver: {solver_name}")
    print(f"Moves: {moves} ({len(moves)} moves)")
    print(f"Elapsed Time: {elapsed_ms} ms (Total wall clock: {total_time} ms)")
    print(f"CUDA Time: {cuda_ms} ms, CUDA Moves: {cuda_count}")
    print(f"Kociemba Time: {kociemba_ms} ms, Kociemba Moves: {kociemba_count}")

    print("\n--- Testing second solve after timeout to verify worker recovery ---")
    easy_cube = scramble_to_state(['R', 'U', 'R\'', 'U\''])
    moves, solver_name, elapsed_ms, cuda_ms, kociemba_ms, cuda_count, kociemba_count = solve_both(easy_cube)
    print(f"Primary Solver: {solver_name}")
    print(f"Solution: {moves}")
    print(f"CUDA Time: {cuda_ms} ms, Kociemba Time: {kociemba_ms} ms")
