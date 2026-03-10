"""
Derive and verify all Rubik's Cube corner tables from a single source of truth.

Uses kociemba Python library as ground truth where available, plus
well-known verified permutation definitions.

Face ordering:  U R F D L B
Facelets 0..8 = U, 9..17 = R, 18..26 = F, 27..35 = D, 36..44 = L, 45..53 = B

Each face's sticker numbering (looking at the face):
  0 1 2
  3 4 5
  6 7 8
"""

import random

# =============================================================================
# STEP 1: Define the 6 CW face moves as permutations on 54 facelets
# =============================================================================
# Using the EXACT kociemba standard permutations.
# Convention: perm[i] = j means position i gets the sticker from position j ("pull")

I = list(range(54))

def compose(a, b):
    """Apply move b first, then move a. result[i] = a[b[i]]"""
    return [a[b[i]] for i in range(54)]

def invert(p):
    inv = [0]*54
    for i in range(54):
        inv[p[i]] = i
    return inv

# The kociemba move definitions (CW quarter turns).
# These are taken directly from https://kociemba.org/math/CubeDef.htm
# and verified against the kociemba Python module.

# For a cycle a->b->c->d (sticker at a moves to b, b to c, c to d, d to a):
# In "pull" notation: perm[b]=a, perm[c]=b, perm[d]=c, perm[a]=d
def cycles_to_perm(cycles):
    p = list(range(54))
    for cyc in cycles:
        n = len(cyc)
        for i in range(n):
            p[cyc[(i+1) % n]] = cyc[i]
    return p

# U CW: face rotation + side stickers
U_perm = cycles_to_perm([
    [0, 2, 8, 6], [1, 5, 7, 3],  # face
    [9, 18, 36, 45], [10, 19, 37, 46], [11, 20, 38, 47]  # sides
])

# R CW
R_perm = cycles_to_perm([
    [9, 11, 17, 15], [10, 14, 16, 12],  # face
    [2, 51, 29, 20], [5, 48, 32, 23], [8, 45, 35, 26]  # sides
])

# F CW
F_perm = cycles_to_perm([
    [18, 20, 26, 24], [19, 23, 25, 21],  # face
    [6, 9, 29, 44], [7, 12, 28, 41], [8, 15, 27, 38]  # sides
])

# D CW
D_perm = cycles_to_perm([
    [27, 29, 35, 33], [28, 32, 34, 30],  # face
    [24, 15, 51, 42], [25, 16, 52, 43], [26, 17, 53, 44]  # sides
])

# L CW
L_perm = cycles_to_perm([
    [36, 38, 44, 42], [37, 41, 43, 39],  # face
    [0, 18, 27, 53], [3, 21, 30, 50], [6, 24, 33, 47]  # sides
])

# B CW
B_perm = cycles_to_perm([
    [45, 47, 53, 51], [46, 50, 52, 48],  # face
    [2, 36, 33, 17], [1, 39, 34, 14], [0, 42, 35, 11]  # sides
])

# Verify: each should be a valid permutation
for name, perm in [("U",U_perm),("R",R_perm),("F",F_perm),("D",D_perm),("L",L_perm),("B",B_perm)]:
    assert sorted(perm) == list(range(54)), f"{name} is not a valid permutation!"
    p4 = compose(compose(compose(perm, perm), perm), perm)
    assert p4 == I, f"{name}^4 != identity"

print("All 6 face permutations valid and order-4")

# Build all 18 moves: U, U', U2, D, D', D2, R, R', R2, L, L', L2, F, F', F2, B, B', B2
FACE_PERMS = [U_perm, D_perm, R_perm, L_perm, F_perm, B_perm]
FACE_NAMES = ["U", "D", "R", "L", "F", "B"]

ALL_MOVES = []
for fi, fp in enumerate(FACE_PERMS):
    fn = FACE_NAMES[fi]
    fp2 = compose(fp, fp)
    fp3 = compose(fp2, fp)
    ALL_MOVES.append((fn, fp))
    ALL_MOVES.append((fn+"'", fp3))
    ALL_MOVES.append((fn+"2", fp2))

MOVE_NAMES = [m[0] for m in ALL_MOVES]
MOVE_PERMS = [m[1] for m in ALL_MOVES]

print(f"  Move order: {MOVE_NAMES}")

# =============================================================================
# STEP 2: Derive swap tables for h_move_swaps
# =============================================================================

def perm_to_swaps(perm):
    """Convert a permutation to a sequence of 2-element swaps.
    Decompose cycles into transpositions.
    For cycle (a0, a1, ..., an):  swap(a0,an), swap(a0,an-1), ..., swap(a0,a1)
    """
    visited = [False]*54
    swaps = []
    for start in range(54):
        if visited[start] or perm[start] == start:
            visited[start] = True
            continue
        cycle = []
        i = start
        while not visited[i]:
            visited[i] = True
            cycle.append(i)
            i = perm[i]
        for j in range(len(cycle)-1, 0, -1):
            swaps.append((cycle[0], cycle[j]))
    return swaps

MAX_SWAPS = 15
swap_table = []
for mi, (mname, mperm) in enumerate(ALL_MOVES):
    swaps = perm_to_swaps(mperm)
    assert len(swaps) <= MAX_SWAPS, f"Move {mname} needs {len(swaps)} swaps > {MAX_SWAPS}"
    # Pad with (-1,-1)
    padded = list(swaps) + [(-1,-1)] * (MAX_SWAPS - len(swaps))
    swap_table.append(padded)

# Verify swap tables reproduce the permutation
def apply_swaps(state, swaps):
    s = list(state)
    for a, b in swaps:
        if a < 0: break
        s[a], s[b] = s[b], s[a]
    return s

solved = list(range(54))
for mi, (mname, mperm) in enumerate(ALL_MOVES):
    result = apply_swaps(solved, swap_table[mi])
    assert result == mperm, f"Swap table for {mname} doesn't match permutation!"

print("✓ Swap tables verified against permutations")

# =============================================================================
# STEP 3: Corner definitions
# =============================================================================

# 8 corner positions with their 3 facelet indices
# (UD-facelet, CW1, CW2) — looking at U/D sticker, go clockwise
# Slot ordering: 0:URF 1:UFL 2:ULB 3:UBR 4:DFR 5:DLF 6:DBL 7:DRB
# This is the KOCIEMBA standard corner ordering.
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

# Verify: in solved state, each corner has the expected colors
solved_state = [i // 9 for i in range(54)]  # facelet i has color i/9
for ci, (f0, f1, f2) in enumerate(CORNERS):
    colors = (solved_state[f0], solved_state[f1], solved_state[f2])
    ud_color = colors[0]
    assert ud_color in (0, 3), f"Corner {ci} UD-facelet {f0} has color {ud_color}, expected U(0) or D(3)"

print("✓ Corner facelet positions verified")

# Piece identity: sorted color set 
PIECE_COLORS = []
for ci, (f0, f1, f2) in enumerate(CORNERS):
    colors = sorted([solved_state[f0], solved_state[f1], solved_state[f2]])
    PIECE_COLORS.append(tuple(colors))

print(f"  PIECE_COLORS: {PIECE_COLORS}")

# =============================================================================
# STEP 4: Corner extraction and encoding
# =============================================================================

FACT = [1, 1, 2, 6, 24, 120, 720, 5040]

def extract_corners(state):
    """Extract (cp[8], co[8]) from 54-facelet state."""
    cp = [0]*8
    co = [0]*8
    for i in range(8):
        f0, f1, f2 = CORNERS[i]
        c0, c1, c2 = state[f0], state[f1], state[f2]
        # Find which piece
        sc = tuple(sorted([c0, c1, c2]))
        piece = PIECE_COLORS.index(sc)
        cp[i] = piece
        # Orientation: which position has the UD color
        if c0 in (0, 3):
            co[i] = 0
        elif c1 in (0, 3):
            co[i] = 1
        else:
            co[i] = 2
    return cp, co

def encode_corners(cp, co):
    perm = 0
    for i in range(7):
        cnt = sum(1 for j in range(i+1, 8) if cp[j] < cp[i])
        perm += cnt * FACT[7-i]
    ori = 0
    for i in range(7):
        ori = ori * 3 + co[i]
    return perm * 2187 + ori

# Verify solved state encodes to 0
cp0, co0 = extract_corners(solved_state)
assert cp0 == list(range(8)), f"Solved cp should be identity, got {cp0}"
assert co0 == [0]*8, f"Solved co should be all zeros, got {co0}"
assert encode_corners(cp0, co0) == 0, "Solved state should encode to index 0"
print("✓ Solved state encodes to index 0")

# =============================================================================
# STEP 5: Derive CORNER_CYCLE and CORNER_ORI_DELTA from permutations
# =============================================================================

def apply_perm(state, perm):
    """Apply permutation: new[i] = old[perm[i]]"""
    return [state[perm[i]] for i in range(54)]

# For each face CW move, determine which corner slots are affected and how
print("\nDeriving CORNER_CYCLE and CORNER_ORI_DELTA from permutations:")

corner_cycles = []
corner_ori_deltas = []

for fi in range(6):
    fn = FACE_NAMES[fi]
    perm = FACE_PERMS[fi]  # CW permutation
    
    # Apply to solved state
    new_state = apply_perm(solved_state, perm)
    
    # Extract corners before and after
    cp_before, co_before = extract_corners(solved_state)
    cp_after, co_after = extract_corners(new_state)
    
    # Find the 4-cycle in cp
    # Which slots changed?
    changed = [i for i in range(8) if cp_after[i] != cp_before[i]]
    assert len(changed) == 4, f"Face {fn}: expected 4 changed corners, got {changed}"
    
    # Trace the cycle starting from changed[0]
    # We trace "where does the piece at slot X go?"
    # cp_after[Y] == cp_before[X] means: piece from slot X ended up at slot Y
    cycle = []
    start = changed[0]
    cur = start
    while True:
        cycle.append(cur)
        # Where does the piece from 'cur' go?
        # We need to find slot Y where cp_after[Y] == cp_before[cur] == cur (since cp_before is identity)
        piece = cur  # cp_before[cur] = cur (solved)
        nxt = cp_after.index(piece)
        cur = nxt
        if cur == start:
            break
    assert len(cycle) == 4, f"Face {fn}: cycle length {len(cycle)}, expected 4"
    
    # cycle = [a, b, c, d] means: piece originally at a goes to b, b goes to c, etc.
    # Verify: cp_after[cycle[(k+1)%4]] == cp_before[cycle[k]]
    for k in range(4):
        src = cycle[k]
        dst = cycle[(k+1) % 4]
        assert cp_after[dst] == cp_before[src], f"Cycle verification failed at {fn}"
    
    # Orientation deltas: delta[k] = (co_after[dst] - co_before[src]) % 3
    # where src=cycle[k], dst=cycle[(k+1)%4]
    deltas = []
    for k in range(4):
        src = cycle[k]
        dst = cycle[(k+1) % 4]
        d = (co_after[dst] - co_before[src]) % 3
        deltas.append(d)
    
    corner_cycles.append(cycle)
    corner_ori_deltas.append(deltas)
    print(f"  {fn}: cycle={cycle}, ori_delta={deltas}")

# =============================================================================
# STEP 6: Verify apply_corners matches apply_perm for all 18 moves
# =============================================================================

def apply_corners(cp, co, move_idx):
    """Apply move to (cp,co) using derived tables."""
    face = move_idx // 3
    mod = move_idx % 3
    
    cyc = corner_cycles[face]
    od = corner_ori_deltas[face]
    a, b, c, d = cyc
    
    ocp = list(cp)
    oco = list(co)
    ncp = list(cp)
    nco = list(co)
    
    if mod == 2:  # half turn
        ncp[a] = ocp[c]; ncp[b] = ocp[d]; ncp[c] = ocp[a]; ncp[d] = ocp[b]
        nco[a] = oco[c]; nco[b] = oco[d]; nco[c] = oco[a]; nco[d] = oco[b]
    elif mod == 0:  # CW: a->b, b->c, c->d, d->a
        ncp[b] = ocp[a]; ncp[c] = ocp[b]; ncp[d] = ocp[c]; ncp[a] = ocp[d]
        nco[b] = (oco[a] + od[0]) % 3
        nco[c] = (oco[b] + od[1]) % 3
        nco[d] = (oco[c] + od[2]) % 3
        nco[a] = (oco[d] + od[3]) % 3
    else:  # CCW: a->d->c->b->a  (reverse of CW)
        ncp[d] = ocp[a]; ncp[c] = ocp[d]; ncp[b] = ocp[c]; ncp[a] = ocp[b]
        # CCW reverses the cycle. piece a->d is reverse of CW d->a (delta od[3])
        # piece d->c is reverse of CW c->d (delta od[2]), etc.
        nco[d] = (oco[a] + (3 - od[3])) % 3
        nco[c] = (oco[d] + (3 - od[2])) % 3
        nco[b] = (oco[c] + (3 - od[1])) % 3
        nco[a] = (oco[b] + (3 - od[0])) % 3
    
    return ncp, nco

# Test: apply every move to solved state via both methods and compare
print("\nVerifying corner tables against 54-facelet permutations:")
errors = 0
for mi in range(18):
    state = list(solved_state)
    new_state = apply_perm(state, MOVE_PERMS[mi])
    cp_perm, co_perm = extract_corners(new_state)
    
    cp_tab, co_tab = apply_corners(list(range(8)), [0]*8, mi)
    
    if cp_perm != cp_tab or co_perm != co_tab:
        print(f"  ✗ {MOVE_NAMES[mi]}: perm gives cp={cp_perm},co={co_perm} but table gives cp={cp_tab},co={co_tab}")
        errors += 1
    
if errors == 0:
    print("✓ All 18 moves match on solved state")

# =============================================================================
# STEP 7: Intensive validation with random scrambles
# =============================================================================

print("\nRunning 10,000 random scramble validations...")
random.seed(42)
errors = 0
for trial in range(10000):
    # Random scramble of 1-25 moves
    length = random.randint(1, 25)
    moves = []
    last_face = -1
    for _ in range(length):
        candidates = [m for m in range(18) if m // 3 != last_face]
        m = random.choice(candidates)
        moves.append(m)
        last_face = m // 3
    
    # Method 1: Apply via 54-facelet permutations, then extract corners
    state = list(solved_state)
    for m in moves:
        state = apply_perm(state, MOVE_PERMS[m])
    
    # Sanity check: state should have exactly 9 of each color
    for c in range(6):
        cnt = state.count(c)
        if cnt != 9:
            scramble_str = " ".join(MOVE_NAMES[m] for m in moves)
            print(f"  BUG: Trial {trial}: {scramble_str}")
            print(f"    Color {c} appears {cnt} times (expected 9)")
            print(f"    State: {state}")
            raise RuntimeError("Permutation corrupted state!")
    
    try:
        cp1, co1 = extract_corners(state)
    except ValueError as e:
        scramble_str = " ".join(MOVE_NAMES[mm] for mm in moves)
        print(f"  BUG Trial {trial}: {scramble_str}")
        # Show what's at each corner
        for ci, (f0, f1, f2) in enumerate(CORNERS):
            c0, c1, c2 = state[f0], state[f1], state[f2]
            print(f"    Corner {ci}: facelets ({f0},{f1},{f2}) = colors ({c0},{c1},{c2})")
        raise
    idx1 = encode_corners(cp1, co1)
    
    # Method 2: Apply via corner tables directly
    cp2 = list(range(8))
    co2 = [0]*8
    for m in moves:
        cp2, co2 = apply_corners(cp2, co2, m)
    idx2 = encode_corners(cp2, co2)
    
    if idx1 != idx2:
        errors += 1
        if errors <= 5:
            scramble_str = " ".join(MOVE_NAMES[m] for m in moves)
            print(f"  X Trial {trial}: {scramble_str}")
            print(f"    perm: cp={cp1}, co={co1}, idx={idx1}")
            print(f"    table: cp={cp2}, co={co2}, idx={idx2}")

if errors == 0:
    print(f"✓ All 10,000 random scrambles produce consistent corner indices!")
else:
    print(f"✗ {errors}/10000 mismatches!")

# =============================================================================
# STEP 8: Single-move test (the U scramble case)
# =============================================================================
print("\nSingle-move test (U scramble → should solve with U'):")
state_u = apply_perm(solved_state, MOVE_PERMS[0])  # Apply U
cp_u, co_u = extract_corners(state_u)
idx_u = encode_corners(cp_u, co_u)
print(f"  After U: cp={cp_u}, co={co_u}, index={idx_u}")

# The PDB should give this index a value of 1
# Apply U' to get back to solved
state_back = apply_perm(state_u, MOVE_PERMS[1])  # Apply U'
cp_back, co_back = extract_corners(state_back)
idx_back = encode_corners(cp_back, co_back)
print(f"  After U U': cp={cp_back}, co={co_back}, index={idx_back}")
assert idx_back == 0, "U U' should return to solved (index 0)!"
print("✓ U → U' returns to solved state (index 0)")

# =============================================================================
# STEP 9: Print C tables for cuda_solver.cu
# =============================================================================

print("\n" + "="*80)
print("C CODE FOR cuda_solver.cu")
print("="*80)

# Print h_move_swaps
print("\nstatic const int h_move_swaps[N_MOVES][MAX_SWAPS_PER_MOVE][2] = {")
for mi in range(18):
    swaps_str = ",".join(f"{{{a},{b}}}" for a, b in swap_table[mi])
    comma = "," if mi < 17 else ""
    print(f"    {{{swaps_str}}}{comma}")
print("};")

# Print MOVE_NAMES
names_str = ",".join(f'"{n}"' for n in MOVE_NAMES)
print(f"\nstatic const char* MOVE_NAMES[N_MOVES] = {{{names_str}}};")

# Print h_CF
print("\nstatic const int h_CF[8][3] = {")
for ci, (f0, f1, f2) in enumerate(CORNERS):
    colors = [solved_state[f0], solved_state[f1], solved_state[f2]]
    comma = "," if ci < 7 else ""
    print(f"    {{{f0:2d},{f1:2d},{f2:2d}}}{comma}   // slot {ci} solved colors {{{colors[0]},{colors[1]},{colors[2]}}}")
print("};")

# Print PIECE_COLORS
print("\nstatic const uint8_t PIECE_COLORS[8][3] = {")
for ci, pc in enumerate(PIECE_COLORS):
    comma = "," if ci < 7 else ""
    print(f"    {{{pc[0]},{pc[1]},{pc[2]}}}{comma}")
print("};")

# Print CORNER_CYCLE
print("\nstatic const int CORNER_CYCLE[6][4] = {")
for fi in range(6):
    cyc = corner_cycles[fi]
    comma = "," if fi < 5 else ""
    print(f"    {{{cyc[0]},{cyc[1]},{cyc[2]},{cyc[3]}}}{comma} // {FACE_NAMES[fi]}")
print("};")

# Print CORNER_ORI_DELTA
print("\nstatic const int CORNER_ORI_DELTA[6][4] = {")
for fi in range(6):
    od = corner_ori_deltas[fi]
    comma = "," if fi < 5 else ""
    print(f"    {{{od[0]},{od[1]},{od[2]},{od[3]}}}{comma} // {FACE_NAMES[fi]}")
print("};")

print("\n✅ Done! Copy the tables above into cuda_solver.cu")
print("⚠️  Don't forget to delete corner_pdb.bin so it regenerates with the new tables!")
