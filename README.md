# 🧊 CUDA Rubik's Cube Solver

A full-stack **optimal** Rubik's Cube solver that uses GPU-accelerated IDA* search with a corner pattern database to find the **shortest possible solution** (in half-turn metric). Includes a React frontend with interactive 3D visualization and live solver comparison against Kociemba's two-phase algorithm.

![Stack](https://img.shields.io/badge/CUDA-C++-76B900?logo=nvidia)
![Stack](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![Stack](https://img.shields.io/badge/Flask-Python-000000?logo=flask)
![Stack](https://img.shields.io/badge/Three.js-WebGL-000000?logo=threedotjs)

---

## How It Works

### The Problem

A standard 3×3 Rubik's Cube has **43 quintillion** possible states (43,252,003,274,489,856,000). Finding the *shortest* solution — the minimum number of moves to reach the solved state — requires searching an enormous game tree. Brute-force search is impossible; the branching factor is 18 (6 faces × 3 turn types) and solutions can be up to 20 moves deep (God's Number in HTM).

### The Algorithm: IDA* with Corner PDB

The solver uses **Iterative Deepening A\*** (IDA*) — a memory-efficient variant of A* that combines depth-first search with an admissible heuristic to guarantee optimal solutions.

```
For depth = heuristic(start) to 22:
    DFS with pruning: skip any branch where depth + h(state) > limit
    If solved → return path (guaranteed optimal)
```

The heuristic is a **Corner Pattern Database (PDB)** — a precomputed lookup table storing the exact minimum number of moves to solve just the 8 corner pieces from any configuration. Since solving the full cube can never take fewer moves than solving just the corners, this is an admissible (never-overestimates) heuristic.

| PDB Property | Value |
|---|---|
| States | **88,179,840** (8! × 3⁷) |
| Size on disk | **84 MB** (`corner_pdb.bin`) |
| Max depth | 11 moves |
| Generation | BFS from solved state |
| Encoding | Lehmer code (perm) × base-3 (orientation) |

### GPU Parallelization

The search is split between CPU and GPU:

1. **CPU (depth 0–6):** Generates a *frontier* of partially-explored states using DFS with PDB pruning
2. **GPU (depth 7+):** Each CUDA thread takes one frontier node and independently searches the remaining depth via DFS

This exploits the exponential branching: at depth 6, there can be up to **4 million** frontier nodes, each assigned to a separate GPU thread for embarrassingly parallel search.

```
CPU: root ──DFS──→ ~1M frontier nodes at depth 6
GPU: 1M threads × DFS from depth 6 to target depth
     └── 256 threads/block, 200K nodes/chunk
```

### Pre-Computed Move Tables

Instead of applying moves to the corner state array and re-encoding each time (expensive), the solver pre-computes transition tables:

| Table | Size | Lookup |
|---|---|---|
| `perm_move[18][40320]` | 1.4 MB | New permutation index after move |
| `ori_move[18][2187]` | 79 KB | New orientation index after move |

Each node expansion is reduced to **two table lookups** + one PDB read, eliminating array manipulation entirely. On GPU, these are accessed via `__ldg()` for L1 cache optimization.

### Pruning Strategies

- **PDB heuristic cutoff:** `depth + pdb[perm*2187 + ori] > max_depth` → prune
- **Same-face elimination:** Never apply the same face twice consecutively (e.g., U then U2)
- **Opposite-face canonicalization:** For opposite faces (U/D, R/L, F/B), enforce ordering to avoid redundant search (U then D is kept; D then U is pruned as equivalent)

---

## Performance

Benchmarked on RTX 2060 (sm_75), Python 3.13, Windows:

| Scramble | Optimal Moves | Solve Time |
|---|---|---|
| `R U R' U'` | 4 | < 1 ms |
| `F R U R' U' F'` | 6 | < 1 ms |
| `R U2 R' U' R U' R'` | 7 | 1 ms |
| `R U R' U' R U R' U'` | 8 | 4 ms |
| `R U F D L B R' U' F' D' L' B'` | 12 | **600 ms** |
| `L F2 R' D B' L U2 F R D' L' B` | 12 | **2,300 ms** |

### CUDA vs Kociemba

The app runs **both** solvers and displays a side-by-side comparison:

| Metric | CUDA (IDA*) | Kociemba (Two-Phase) |
|---|---|---|
| **Goal** | Optimal (fewest moves) | Fast (any short solution) |
| **Solution quality** | Provably shortest | Typically 18–22 moves |
| **12-move scramble** | 12 moves in ~600–2300 ms | ~19 moves in ~30 ms |
| **Algorithm** | IDA* + corner PDB + GPU | Pre-computed pruning tables |
| **Hardware** | GPU (CUDA) | CPU only |

Kociemba is faster in raw wall-clock time. CUDA finds shorter solutions — often **5–10 fewer moves** for the same scramble.

---

## Architecture

```
┌──────────────────────────────────────────┐
│             React Frontend               │
│  TwistyPlayer (3D) + Face Painter + UI   │
│              Port 3000                   │
└──────────────┬───────────────────────────┘
               │ HTTP (JSON)
┌──────────────▼───────────────────────────┐
│           Flask Backend                  │
│   /solve  /scramble  /health             │
│   Runs CUDA + Kociemba, returns both     │
│              Port 5000                   │
└──────┬───────────────────┬───────────────┘
       │                   │
┌──────▼──────┐    ┌───────▼──────┐
│ cuda_solver │    │   kociemba   │
│   (.pyd)    │    │   (pip pkg)  │
│ CUDA C ext  │    │  Python/C    │
│ IDA* + PDB  │    │  Two-phase   │
│ GPU kernel  │    │  CPU only    │
└─────────────┘    └──────────────┘
```

---

## Project Structure

```
rubiks_solver/
├── backend/
│   ├── cuda_solver.cu      # CUDA C — IDA* solver, PDB gen, move tables, Python C API
│   ├── app.py              # Flask server — endpoints, dual-solver comparison
│   ├── build_windows.py    # nvcc build script → cuda_solver.pyd
│   ├── setup.py            # Linux build via setuptools
│   ├── bench_solver.py     # Performance benchmarks (6 scrambles)
│   ├── test_solver.py      # Correctness tests (all single-move scrambles)
│   ├── verify_tables.py    # Derives & validates all move/corner tables
│   ├── diagnose_pdb.py     # PDB integrity diagnostics
│   └── test_scramble.py    # Scramble generation tests
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Main UI — face painter, 3D viewer, comparison panel
│   │   └── main.jsx        # React entry point
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## Quick Start

### Prerequisites

- **NVIDIA GPU** with CUDA support (tested on RTX 2060, sm_75)
- **CUDA Toolkit** (nvcc on PATH)
- **Python 3.10+**
- **Node.js 18+**

### Backend

```bash
cd backend

# Build CUDA extension
python build_windows.py          # Windows → cuda_solver.pyd
# python setup.py build_ext --inplace  # Linux alternative

# Install Python dependencies
pip install flask flask-cors kociemba

# Run server (first launch generates 84 MB PDB — ~30 seconds, cached afterward)
python app.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev    # → http://localhost:3000
```

### Usage

1. Open `http://localhost:3000`
2. Click **🎲 SCRAMBLE** to generate a random cube state
3. Click **SOLVE** to find the optimal solution
4. Watch the 3D playback and compare CUDA vs Kociemba results

---

## Technical Details

### Numbers at a Glance

| | |
|---|---|
| Cube state space | 4.3 × 10¹⁹ |
| Corner PDB states | 88,179,840 |
| PDB size | 84 MB |
| Move table size | ~1.5 MB |
| GPU frontier (max) | 4,000,000 nodes |
| Kernel block size | 256 threads |
| Chunk size | 200,000 nodes/launch |
| Max search depth | 22 (God's Number in HTM is 20) |
| Branching factor | 18 (reduced to ~15 avg with pruning) |

### Corner Encoding

Each corner state is encoded as two indices:
- **Permutation** (0–40,319): Lehmer code of the 8-corner permutation
- **Orientation** (0–2,186): Base-3 encoding of 7 corner twists (8th determined by mod-3 constraint)

Combined index: `perm × 2187 + ori` → single PDB lookup.

### FrontierNode (GPU)

```c
typedef struct {
    uint8_t  state[54];    // Full cube facelets (for solved check)
    uint16_t perm_idx;     // Corner permutation index
    uint16_t ori_idx;      // Corner orientation index
    int      path[6];      // Moves taken to reach this node
} FrontierNode;            // ~84 bytes per node
```

### API

**POST /solve**
```json
// Request
{ "cube_string": "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB" }

// Response
{
  "solution": ["R", "U", "R'", "U'"],
  "move_count": 4,
  "solver": "CUDA",
  "solve_time_ms": 0.85,
  "comparison": {
    "cuda_ms": 0.85,
    "kociemba_ms": 28.4,
    "cuda_moves": 4,
    "kociemba_moves": 7
  }
}
```

---

## Build Targets

| Target | Command | Output |
|---|---|---|
| CUDA extension (Windows) | `python build_windows.py` | `cuda_solver.pyd` |
| CUDA extension (Linux) | `python setup.py build_ext --inplace` | `cuda_solver.so` |
| Frontend dev server | `npm run dev` | localhost:3000 |
| Run benchmarks | `python bench_solver.py` | Console output |
| Run correctness tests | `python test_solver.py` | Pass/fail for all 1-move scrambles |
| Validate tables | `python verify_tables.py` | Derives tables from Kociemba notation |

---

## GPU Architecture Notes

- Targets **sm_75** (Turing) by default; edit `build_windows.py` for other architectures
- PDB and move tables stored in GPU **global memory** (total ~86 MB)
- Move swap tables (54-facelet) stored in `__constant__` memory for fast broadcast reads
- Corner cycle/orientation tables also in `__constant__` memory
- Move table reads use `__ldg()` intrinsic for L1 cache hints
- Early termination via `atomicCAS` on `d_found_flag` — once any thread finds a solution, all others exit

---

## License

MIT
