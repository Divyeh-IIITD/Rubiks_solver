import cuda_solver
import kociemba
import time
import multiprocessing
import sys
sys.path.insert(0, '.')
from app import scramble_to_state

def cuda_worker(cube, queue):
    import cuda_solver as cs
    result = cs.solve(cube)
    queue.put(result)

if __name__ == '__main__':
    # Hard scramble that takes CUDA a long time
    cube = scramble_to_state(['R','U','F','D','L','B','R2','U2','F2','D2','L2','B2','R','U','F','D','L','B','R2','U2'])
    print("Cube:", cube)

    print("\n--- Testing CUDA with 3s timeout (multiprocessing) ---")
    queue = multiprocessing.Queue()
    proc = multiprocessing.Process(target=cuda_worker, args=(cube, queue), daemon=True)
    t0 = time.perf_counter()
    proc.start()
    proc.join(timeout=3.0)
    elapsed = round((time.perf_counter() - t0) * 1000, 2)

    if proc.is_alive():
        proc.kill()
        proc.join()
        print(f"CUDA timed out after {elapsed} ms — killed process")
        print("Falling back to Kociemba...")
        t0 = time.perf_counter()
        ks = kociemba.solve(cube)
        kt = round((time.perf_counter() - t0) * 1000, 2)
        print(f"Kociemba: {ks} ({len(ks.split())} moves, {kt} ms)")
    else:
        sol = queue.get_nowait()
        print(f"CUDA finished in {elapsed} ms")
        print(f"Result: {sol} ({len(sol.split())} moves)")
