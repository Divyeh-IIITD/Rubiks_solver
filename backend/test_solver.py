"""Quick end-to-end test for the CUDA solver."""
import sys
sys.path.insert(0, '.')
import cuda_solver

# The PDB will auto-generate on first call (takes several minutes).
# After that it's cached in corner_pdb.bin.

print("Testing single-move scrambles...")
print("(PDB will generate on first call if not cached)\n")

# Test: U scramble → should find U' (1 move)
# Cube string: apply U to solved state
# Solved = UUUUUUUUURRRRRRRRR FFFFFFFFFDDDDDDDDLLLLLLLLLBBBBBBBBB
# After U CW: top row of R,F,L,B faces rotate

# Build cube strings using app.py's logic
def apply_move(state, move):
    state = list(state)
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

COLOR_MAP = "URFDLB"
solved = [i // 9 for i in range(54)]

def state_to_str(state):
    return ''.join(COLOR_MAP[c] for c in state)

tests = [
    ("U", "U'"),
    ("R", "R'"),
    ("F", "F'"),
    ("D", "D'"),
    ("L", "L'"),
    ("B", "B'"),
    ("U'", "U"),
    ("U2", "U2"),
]

for scramble, expected_inverse in tests:
    state = apply_move(solved, scramble)
    cube_str = state_to_str(state)
    result = cuda_solver.solve(cube_str)
    expected_len = 1 if "2" not in scramble else 1
    actual_len = len(result.split()) if result else 0
    status = "PASS" if actual_len == 1 else "FAIL"
    print(f"  {status}: Scramble={scramble:3s} → Solution='{result}' (expected 1 move)")

print("\nDone!")
