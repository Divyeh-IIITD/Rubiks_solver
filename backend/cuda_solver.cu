#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <cuda_runtime.h>

#define N_MOVES            18
#define MAX_DEPTH          20
#define BLOCK_SIZE         256
#define MAX_SWAPS_PER_MOVE 15

typedef struct { uint8_t f[54]; } Cube;

static const int h_move_swaps[N_MOVES][MAX_SWAPS_PER_MOVE][2] = {
    // 0: U
    {{0,2},{0,8},{0,6},{1,3},{1,7},{1,5},{9,45},{9,36},{9,18},{10,46},{10,37},{10,19},{11,47},{11,38},{11,20}},
    // 1: U'
    {{0,6},{0,8},{0,2},{1,5},{1,7},{1,3},{9,18},{9,36},{9,45},{10,19},{10,37},{10,46},{11,20},{11,38},{11,47}},
    // 2: U2
    {{0,8},{2,6},{1,7},{3,5},{9,36},{10,37},{11,38},{18,45},{19,46},{20,47},{-1,-1},{-1,-1},{-1,-1},{-1,-1},{-1,-1}},
    // 3: D
    {{27,29},{27,35},{27,33},{28,30},{28,34},{28,32},{24,15},{24,51},{24,42},{25,16},{25,52},{25,43},{26,17},{26,53},{26,44}},
    // 4: D'
    {{27,33},{27,35},{27,29},{28,32},{28,34},{28,30},{24,42},{24,51},{24,15},{25,43},{25,52},{25,16},{26,44},{26,53},{26,17}},
    // 5: D2
    {{27,35},{29,33},{28,34},{30,32},{24,51},{25,52},{26,53},{15,42},{16,43},{17,44},{-1,-1},{-1,-1},{-1,-1},{-1,-1},{-1,-1}},
    // 6: R
    {{9,11},{9,17},{9,15},{10,12},{10,16},{10,14},{2,18},{2,47},{2,27},{5,21},{5,50},{5,30},{8,24},{8,53},{8,33}},
    // 7: R'
    {{9,15},{9,17},{9,11},{10,14},{10,16},{10,12},{2,27},{2,47},{2,18},{5,30},{5,50},{5,21},{8,33},{8,53},{8,24}},
    // 8: R2
    {{9,17},{11,15},{10,16},{12,14},{2,47},{5,50},{8,53},{18,27},{21,30},{24,33},{-1,-1},{-1,-1},{-1,-1},{-1,-1},{-1,-1}},
    // 9: L
    {{36,38},{36,44},{36,42},{37,39},{37,43},{37,41},{0,45},{0,27},{0,18},{3,48},{3,30},{3,21},{6,51},{6,33},{6,24}},
    // 10: L'
    {{36,42},{36,44},{36,38},{37,41},{37,43},{37,39},{0,18},{0,27},{0,45},{3,21},{3,30},{3,48},{6,24},{6,33},{6,51}},
    // 11: L2
    {{36,44},{38,42},{37,43},{39,41},{0,27},{3,30},{6,33},{18,45},{21,48},{24,51},{-1,-1},{-1,-1},{-1,-1},{-1,-1},{-1,-1}},
    // 12: F
    {{18,20},{18,26},{18,24},{19,21},{19,25},{19,23},{6,44},{6,29},{6,9},{7,41},{7,28},{7,12},{8,38},{8,27},{8,15}},
    // 13: F'
    {{18,24},{18,26},{18,20},{19,23},{19,25},{19,21},{6,9},{6,29},{6,44},{7,12},{7,28},{7,41},{8,15},{8,27},{8,38}},
    // 14: F2
    {{18,26},{20,24},{19,25},{21,23},{6,29},{7,28},{8,27},{9,44},{12,41},{15,38},{-1,-1},{-1,-1},{-1,-1},{-1,-1},{-1,-1}},
    // 15: B
    {{45,47},{45,53},{45,51},{46,48},{46,52},{46,50},{2,11},{2,35},{2,36},{1,14},{1,34},{1,39},{0,17},{0,33},{0,42}},
    // 16: B'
    {{45,51},{45,53},{45,47},{46,50},{46,52},{46,48},{2,36},{2,35},{2,11},{1,39},{1,34},{1,14},{0,42},{0,33},{0,17}},
    // 17: B2
    {{45,53},{47,51},{46,52},{48,50},{0,35},{1,34},{2,33},{11,36},{14,39},{17,42},{-1,-1},{-1,-1},{-1,-1},{-1,-1},{-1,-1}},
};

static const char* MOVE_NAMES[N_MOVES] = {
    "U","U'","U2","D","D'","D2","R","R'","R2","L","L'","L2","F","F'","F2","B","B'","B2"
};

__constant__ int d_move_swaps[N_MOVES][MAX_SWAPS_PER_MOVE][2];

// ─── CPU ──────────────────────────────────────────────────────────────────────

static void cpu_apply(Cube* c, int m) {
    for (int s = 0; s < MAX_SWAPS_PER_MOVE; s++) {
        int a = h_move_swaps[m][s][0];
        int b = h_move_swaps[m][s][1];
        if (a < 0) break;
        uint8_t t = c->f[a]; c->f[a] = c->f[b]; c->f[b] = t;
    }
}

static int cpu_solved(const Cube* c) {
    for (int face = 0; face < 6; face++)
        for (int i = 0; i < 9; i++)
            if (c->f[face*9+i] != (uint8_t)face) return 0;
    return 1;
}

// ─── GPU ──────────────────────────────────────────────────────────────────────

__device__ void gpu_apply(uint8_t* f, int m) {
    for (int s = 0; s < MAX_SWAPS_PER_MOVE; s++) {
        int a = d_move_swaps[m][s][0];
        int b = d_move_swaps[m][s][1];
        if (a < 0) break;
        uint8_t t = f[a]; f[a] = f[b]; f[b] = t;
    }
}

__device__ int gpu_solved(const uint8_t* f) {
    for (int face = 0; face < 6; face++)
        for (int i = 0; i < 9; i++)
            if (f[face*9+i] != (uint8_t)face) return 0;
    return 1;
}

__global__ void kernel_search(
    const uint8_t* __restrict__ init,
    int  depth,
    int  n_seq,
    int* result_seq,
    int* found
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= n_seq || *found >= 0) return;

    int moves[MAX_DEPTH];
    int tmp = tid;
    for (int d = depth-1; d >= 0; d--) {
        moves[d] = tmp % N_MOVES;
        tmp      /= N_MOVES;
    }

    for (int d = 1; d < depth; d++)
        if (moves[d]/3 == moves[d-1]/3) return;

    uint8_t state[54];
    for (int i = 0; i < 54; i++) state[i] = init[i];
    for (int d = 0; d < depth; d++) gpu_apply(state, moves[d]);

    if (gpu_solved(state))
        if (atomicCAS(found, -1, tid) == -1)
            *result_seq = tid;
}

// ─── GPU SEARCH ───────────────────────────────────────────────────────────────

static int gpu_search(const Cube* init, int depth, int* out_moves) {
    int n_seq = 1;
    for (int d = 0; d < depth; d++) n_seq *= N_MOVES;

    uint8_t* d_init;
    int*     d_result;
    int*     d_found;
    cudaMalloc(&d_init,   54);
    cudaMalloc(&d_result, sizeof(int));
    cudaMalloc(&d_found,  sizeof(int));
    cudaMemcpy(d_init, init->f, 54, cudaMemcpyHostToDevice);
    int h_found = -1;
    cudaMemcpy(d_found, &h_found, sizeof(int), cudaMemcpyHostToDevice);

    int blocks = (n_seq + BLOCK_SIZE - 1) / BLOCK_SIZE;
    kernel_search<<<blocks, BLOCK_SIZE>>>(d_init, depth, n_seq, d_result, d_found);
    cudaDeviceSynchronize();
    cudaMemcpy(&h_found, d_found, sizeof(int), cudaMemcpyDeviceToHost);

    int found = 0;
    if (h_found >= 0) {
        int seq = h_found;
        for (int d = depth-1; d >= 0; d--) {
            out_moves[d] = seq % N_MOVES;
            seq /= N_MOVES;
        }
        found = 1;
    }
    cudaFree(d_init); cudaFree(d_result); cudaFree(d_found);
    return found;
}

// ─── CPU IDA* ─────────────────────────────────────────────────────────────────

static int g_found;
static int g_path[MAX_DEPTH];

static void dfs(Cube state, int depth, int max_depth, int last_face, int* path) {
    if (g_found) return;
    if (depth == max_depth) {
        if (cpu_solved(&state)) {
            memcpy(g_path, path, max_depth * sizeof(int));
            g_found = 1;
        }
        return;
    }
    for (int m = 0; m < N_MOVES; m++) {
        if (m/3 == last_face) continue;
        path[depth] = m;
        Cube next = state;
        cpu_apply(&next, m);
        dfs(next, depth+1, max_depth, m/3, path);
        if (g_found) return;
    }
}

// ─── PARSE ────────────────────────────────────────────────────────────────────

static int parse_cube(const char* s, Cube* c) {
    if (strlen(s) != 54) return 0;
    const char* fc = "URFDLB";
    for (int i = 0; i < 54; i++) {
        const char* p = strchr(fc, s[i]);
        if (!p) return 0;
        c->f[i] = (uint8_t)(p - fc);
    }
    return 1;
}

// ─── VERIFY MOVE TABLE ───────────────────────────────────────────────────────
// Apply move then its inverse — should return to solved state
static void verify_moves() {
    fprintf(stderr, "Verifying move table...\n");
    for (int m = 0; m < N_MOVES; m += 3) {
        // For each face: apply CW 4 times should = identity
        Cube c;
        for (int i = 0; i < 54; i++) c.f[i] = i % 6; // doesn't matter, use solved
        for (int i = 0; i < 54; i++) c.f[i] = i / 9;
        Cube orig = c;
        for (int t = 0; t < 4; t++) cpu_apply(&c, m);
        int ok = 1;
        for (int i = 0; i < 54; i++) if (c.f[i] != orig.f[i]) { ok = 0; break; }
        fprintf(stderr, "  Move %s x4 = identity: %s\n", MOVE_NAMES[m], ok ? "OK" : "FAIL");
    }
}

// ─── MAIN ────────────────────────────────────────────────────────────────────

int main(int argc, char** argv) {
    if (argc < 2) { fprintf(stderr, "Usage: cuda_solver <54-char-cube>\n"); return 1; }

    Cube cube;
    if (!parse_cube(argv[1], &cube)) { fprintf(stderr, "Invalid cube string\n"); return 1; }

    fprintf(stderr, "Parsed: ");
    for (int i = 0; i < 54; i++) fprintf(stderr, "%d", cube.f[i]);
    fprintf(stderr, "\nSolved: %d\n", cpu_solved(&cube));

    verify_moves();

    if (cpu_solved(&cube)) { printf("\n"); return 0; }

    cudaMemcpyToSymbol(d_move_swaps, h_move_swaps, sizeof(h_move_swaps));

    int out_moves[MAX_DEPTH];
    int found = 0;

    // CPU-only IDA* for all depths (debug mode)
    int path[MAX_DEPTH];
    for (int d = 1; d <= MAX_DEPTH && !found; d++) {
        fprintf(stderr, "Searching depth %d...\n", d);
        g_found = 0;
        dfs(cube, 0, d, -1, path);
        if (g_found) {
            found = 1;
            for (int i = 0; i < d; i++) {
                if (i) printf(" ");
                printf("%s", MOVE_NAMES[g_path[i]]);
            }
            printf("\n");
            return 0;
        }
    }

    fprintf(stderr, "No solution found\n");
    return 1;
}
