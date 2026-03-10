"""
Diagnose PDB consistency: load the PDB from disk, compute corner indices 
using the VERIFIED Python tables, and check if the stored distances make sense.
"""
import struct, sys

# ── Verified corner tables (from verify_tables.py) ──
CORNERS = [
    (8, 9, 20),    # 0: URF
    (6, 18, 38),   # 1: UFL
    (0, 36, 47),   # 2: ULB
    (2, 45, 11),   # 3: UBR
    (29, 26, 15),  # 4: DFR
    (27, 44, 24),  # 5: DLF
    (33, 53, 42),  # 6: DBL
    (35, 17, 51),  # 7: DRB
]
PIECE_COLORS = [(0,1,2),(0,2,4),(0,4,5),(0,1,5),(1,2,3),(2,3,4),(3,4,5),(1,3,5)]
FACT = [1,1,2,6,24,120,720,5040]

def extract_corners(state):
    cp, co = [0]*8, [0]*8
    for i in range(8):
        f0, f1, f2 = CORNERS[i]
        c0, c1, c2 = state[f0], state[f1], state[f2]
        sc = tuple(sorted([c0, c1, c2]))
        cp[i] = PIECE_COLORS.index(sc)
        if c0 in (0,3): co[i] = 0
        elif c1 in (0,3): co[i] = 1
        else: co[i] = 2
    return cp, co

def encode_corners(cp, co):
    perm = 0
    for i in range(7):
        cnt = sum(1 for j in range(i+1,8) if cp[j] < cp[i])
        perm += cnt * FACT[7-i]
    ori = 0
    for i in range(7):
        ori = ori*3 + co[i]
    return perm * 2187 + ori

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

# ── Load PDB ──
print("Loading PDB from disk...")
with open("corner_pdb.bin", "rb") as f:
    pdb = f.read()
print(f"PDB size: {len(pdb)} bytes")

# Check solved state
solved = [i // 9 for i in range(54)]
cp0, co0 = extract_corners(solved)
idx0 = encode_corners(cp0, co0)
print(f"\nSolved state: cp={cp0}, co={co0}, index={idx0}, PDB[{idx0}]={pdb[idx0]}")

# Check distribution
from collections import Counter
dist = Counter(pdb)
print(f"\nPDB value distribution:")
for v in sorted(dist.keys()):
    print(f"  depth {v:3d}: {dist[v]:>12,} states")

# Check each single move
print(f"\nSingle-move scrambles (should all have PDB value = 1):")
moves = ["U","U'","U2","D","D'","D2","R","R'","R2","L","L'","L2","F","F'","F2","B","B'","B2"]
for m in moves:
    state = apply_move(solved, m)
    cp, co = extract_corners(state)
    idx = encode_corners(cp, co)
    val = pdb[idx]
    status = "OK" if val == 1 else "BAD"
    print(f"  {m:3s}: cp={cp}, co={co}, idx={idx:>10d}, PDB={val} {status}")

# Also verify: apply_corners (cycle-table) method gives same index
print("\n── Verifying cycle-table consistency ──")
corner_cycles = [[0,1,2,3],[4,7,6,5],[0,3,7,4],[1,5,6,2],[0,4,5,1],[2,6,7,3]]
corner_ori_deltas = [[0,0,0,0],[0,0,0,0],[1,2,1,2],[2,1,2,1],[2,1,2,1],[2,1,2,1]]

def apply_corners_table(cp, co, move_idx):
    face = move_idx // 3
    mod = move_idx % 3
    cyc = corner_cycles[face]
    od = corner_ori_deltas[face]
    a, b, c, d = cyc
    ocp, oco = list(cp), list(co)
    ncp, nco = list(cp), list(co)
    if mod == 2:
        ncp[a]=ocp[c]; ncp[b]=ocp[d]; ncp[c]=ocp[a]; ncp[d]=ocp[b]
        nco[a]=oco[c]; nco[b]=oco[d]; nco[c]=oco[a]; nco[d]=oco[b]
    elif mod == 0:
        ncp[b]=ocp[a]; ncp[c]=ocp[b]; ncp[d]=ocp[c]; ncp[a]=ocp[d]
        nco[b]=(oco[a]+od[0])%3; nco[c]=(oco[b]+od[1])%3
        nco[d]=(oco[c]+od[2])%3; nco[a]=(oco[d]+od[3])%3
    else:
        ncp[d]=ocp[a]; ncp[c]=ocp[d]; ncp[b]=ocp[c]; ncp[a]=ocp[b]
        nco[d]=(oco[a]+(3-od[3]))%3; nco[c]=(oco[d]+(3-od[2]))%3
        nco[b]=(oco[c]+(3-od[1]))%3; nco[a]=(oco[b]+(3-od[0]))%3
    return ncp, nco

move_names = ["U","U'","U2","D","D'","D2","R","R'","R2","L","L'","L2","F","F'","F2","B","B'","B2"]

print("Comparing 54-facelet extraction vs cycle-table for each move:")
mismatches = 0
for mi in range(18):
    # Method 1: 54-facelet
    state = apply_move(solved, move_names[mi])
    cp1, co1 = extract_corners(state)
    idx1 = encode_corners(cp1, co1)
    
    # Method 2: cycle-table
    cp2, co2 = apply_corners_table(list(range(8)), [0]*8, mi)
    idx2 = encode_corners(cp2, co2)
    
    if idx1 != idx2:
        mismatches += 1
        print(f"  MISMATCH {move_names[mi]:3s}: facelet idx={idx1} (cp={cp1},co={co1}) vs table idx={idx2} (cp={cp2},co={co2})")
    
if mismatches == 0:
    print("  All 18 moves consistent!")
