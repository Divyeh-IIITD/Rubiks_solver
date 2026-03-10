"""Diagnose the U+L composition bug."""
def cycles_to_perm(cycles):
    p = list(range(54))
    for cyc in cycles:
        n = len(cyc)
        for i in range(n):
            p[cyc[(i+1) % n]] = cyc[i]
    return p

def compose(a, b):
    """Compose permutations: first apply b, then a. result[i] = a[b[i]]"""
    return [a[b[i]] for i in range(54)]

def apply_perm(state, perm):
    """Apply perm to state: new[i] = old[perm[i]]"""
    return [state[perm[i]] for i in range(54)]

import kociemba

U_perm = cycles_to_perm([[0,2,8,6],[1,5,7,3],[9,18,36,45],[10,19,37,46],[11,20,38,47]])
L_perm = cycles_to_perm([[36,38,44,42],[37,41,43,39],[0,18,27,47],[3,21,30,50],[6,24,33,53]])

solved = list('UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB')

# Method 1: apply U then L sequentially
after_U = apply_perm(solved, U_perm)
after_UL_seq = apply_perm(after_U, L_perm)

# Method 2: compose UL permutation, then apply
UL_perm = compose(L_perm, U_perm)  # first U, then L
after_UL_comp = apply_perm(solved, UL_perm)

print(f"Sequential: {''.join(after_UL_seq)}")
print(f"Composed:   {''.join(after_UL_comp)}")
print(f"Same: {after_UL_seq == after_UL_comp}")

# Also try using kociemba to get the correct U L state
# by applying kociemba's own understanding
# The kociemba module uses a specific input format
# Let's just verify the individual states are correct
print(f"\nAfter U: {''.join(after_U)}")
print(f"After U (kociemba): {kociemba.solve(''.join(after_U))}")

print(f"\nAfter L: {''.join(apply_perm(solved, L_perm))}")
print(f"After L (kociemba): {kociemba.solve(''.join(apply_perm(solved, L_perm)))}")

# Let me try a DIFFERENT approach: Use app.py's apply_move to build the reference state
# and compare
print("\n--- Using app.py's apply_move as reference ---")
import sys
sys.path.insert(0, r'c:\Users\Divyeh\OneDrive\Desktop\rubiks_solver\backend')

# Copy the apply_move from app.py
def apply_move_ref(state, move):
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

ref_state = list('UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB')
apply_move_ref(ref_state, 'U')
print(f"Ref after U: {''.join(ref_state)}")
print(f"My after U:  {''.join(after_U)}")
print(f"Match: {ref_state == after_U}")

ref_UL = list(ref_state)
apply_move_ref(ref_UL, 'L')
print(f"\nRef after UL: {''.join(ref_UL)}")
print(f"My after UL:  {''.join(after_UL_seq)}")
print(f"Match: {ref_UL == after_UL_seq}")

# Check ref UL with kociemba
try:
    print(f"Ref UL kociemba: {kociemba.solve(''.join(ref_UL))}")
except Exception as e:
    print(f"Ref UL kociemba: ERROR {e}")

# Compare where they differ
if ref_UL != after_UL_seq:
    print("\nDifferences:")
    for i in range(54):
        if ref_UL[i] != after_UL_seq[i]:
            print(f"  pos {i}: ref={ref_UL[i]}, mine={after_UL_seq[i]}")

