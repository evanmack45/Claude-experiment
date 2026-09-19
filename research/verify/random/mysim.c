/* mysim.c -- independent re-implementation (verifier) of the random-configuration
 * Langton's ant experiment, written from research/CONVENTIONS.md.
 *
 * Differences from the finder's randexp.c (deliberate, for independence):
 *  - the complete turn sequence t[1..n] and the running bounding box after every
 *    step are stored in flat arrays (no ring buffer); after the run stops the
 *    onset s = max{k : t[k] != t[k+104]} is RECOMPUTED from the full array and
 *    t[k]==t[k+104] is re-verified for every k in s+1..n-104;
 *  - the true maximum |coordinate| over ALL steps of the run is tracked;
 *  - grid is 8192x8192 (origin 4096) so a 4096-boundary hit in the finder's code
 *    would show up here as a normal run.
 *
 * Usage:
 *   ./mysim run   k p seed nsamples cap outcsv     one CSV row per sample (finder's 18-column layout + maxabs column)
 *   ./mysim u32   k p seed nsamples cap outprefix  onset list (uint32, sample order) + summary line to stderr
 *   ./mysim one   k p seed idx cap                 JSON for one sample
 *   ./mysim dump  k p seed idx                     black cells of one sample
 *   ./mysim cells cellsfile cap                    run an explicit cell list ("x y" per line)
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

#define G 8192
#define O (G/2)
#define P 104
#define NPER 20
#define MARG 20

static uint8_t *grid;           /* colour */
static int32_t *dirty; static long ndirty;
static uint8_t *T;              /* T[n] turn at step n: 1 = R (white), 0 = L (black) */
static int16_t *PX, *PY;        /* position after step n (PX[0]=origin) relative to origin */
static int16_t *BX0, *BY0, *BX1, *BY1; /* bbox of {origin, initial black, cells modified in steps 1..n} */
static int64_t CAPMAX;

/* --- RNG as documented in research/random/README.md --- */
static uint64_t st;
static uint64_t nxt(void){ st += 0x9E3779B97F4A7C15ULL; uint64_t z = st;
  z = (z ^ (z>>30)) * 0xBF58476D1CE4E5B9ULL; z = (z ^ (z>>27)) * 0x94D049BB133111EBULL; return z ^ (z>>31); }

static int ncell; static int16_t *CX, *CY; /* black cells */
static void gen(int k, double p, uint64_t seed, uint64_t idx){
  uint64_t p1000 = (uint64_t) llround(1000.0*p);
  st = seed*0x9E3779B97F4A7C15ULL + idx*0xBF58476D1CE4E5B9ULL + (uint64_t)k*0x94D049BB133111EBULL + p1000*0xD6E8FEB86659FD93ULL;
  int xmin = -(k/2);  /* -floor(k/2) for odd k, -k/2 for even k */
  ncell = 0;
  for (int y = 0; y < k; y++) for (int x = 0; x < k; x++) {   /* order i = x + k*y, i.e. x fastest */
    uint64_t r = nxt();
    double u = (double)(r >> 11) / 9007199254740992.0;
    if (u < p) { CX[ncell] = xmin + x; CY[ncell] = xmin + y; ncell++; }
  }
}

typedef struct { const char *outcome; int64_t s, n; int dx, dy; int fx, fy; int bx0, by0, bx1, by1; int maxabs; int nblack; int64_t periods; int mism_after_s; } res_t;

static int NOSTOP = 0;
static res_t simulate(int64_t cap){
  res_t R; memset(&R, 0, sizeof R);
  ndirty = 0;
  int bx0=0,by0=0,bx1=0,by1=0;
  for (int i = 0; i < ncell; i++) { int32_t id = (CY[i]+O)*G + (CX[i]+O); grid[id] = 1; dirty[ndirty++] = id;
    if (CX[i]<bx0) bx0=CX[i]; if (CX[i]>bx1) bx1=CX[i]; if (CY[i]<by0) by0=CY[i]; if (CY[i]>by1) by1=CY[i]; }
  R.nblack = ncell;
  int x=0,y=0,d=0; /* d: 0=N 1=E 2=S 3=W */
  static const int DX[4]={0,1,0,-1}, DY[4]={1,0,-1,0};
  PX[0]=0; PY[0]=0; BX0[0]=bx0; BY0[0]=by0; BX1[0]=bx1; BY1[0]=by1;
  int64_t L = 0, n = 0; int maxabs = 0; const char *outcome = "cap"; int dx=0, dy=0;
  while (n < cap) {
    n++;
    int32_t id = (y+O)*G + (x+O);
    uint8_t c = grid[id];
    if (c) { d = (d+3)&3; T[n] = 0; } else { d = (d+1)&3; T[n] = 1; }   /* black: left, white: right */
    if (c == 0) { /* first time a white cell is written: mark dirty (black cells already dirty) */ }
    dirty[ndirty++] = id;
    grid[id] = c ^ 1;
    if (x<bx0) bx0=x; if (x>bx1) bx1=x; if (y<by0) by0=y; if (y>by1) by1=y;
    x += DX[d]; y += DY[d];
    if (abs(x) > maxabs) maxabs = abs(x); if (abs(y) > maxabs) maxabs = abs(y);
    if (abs(x) >= O-2 || abs(y) >= O-2) { outcome = "boundary"; break; }
    PX[n]=x; PY[n]=y; BX0[n]=bx0; BY0[n]=by0; BX1[n]=bx1; BY1[n]=by1;
    if (n > P && T[n] != T[n-P]) L = n - P;
    if (n >= L + P + NPER*P) {
      dx = PX[n]-PX[n-P]; dy = PY[n]-PY[n-P];
      if (dx && dy) {
        int ex = dx>0 ? (x - BX1[L] >= MARG) : (BX0[L] - x >= MARG);
        int ey = dy>0 ? (y - BY1[L] >= MARG) : (BY0[L] - y >= MARG);
        if (ex && ey && !NOSTOP) { outcome = "certified"; break; }
      }
    }
  }
  for (long i = 0; i < ndirty; i++) grid[dirty[i]] = 0;
  /* post-hoc recomputation of s from the full turn array, by definition */
  int64_t s = 0;
  for (int64_t k = n - P; k >= 1; k--) if (T[k] != T[k+P]) { s = k; break; }
  int mism = 0; for (int64_t k = s+1; k + P <= n; k++) if (T[k] != T[k+P]) mism++;
  if (s != L) { fprintf(stderr, "INTERNAL: s(post-hoc)=%lld != L(running)=%lld\n", (long long)s, (long long)L); exit(2); }
  if (!strcmp(outcome,"cap") && n >= L + P + NPER*P) outcome = "nontravel";
  R.outcome = outcome; R.s = s; R.n = n; R.dx = dx; R.dy = dy; R.fx = x; R.fy = y;
  R.bx0 = BX0[s]; R.by0 = BY0[s]; R.bx1 = BX1[s]; R.by1 = BY1[s]; R.maxabs = maxabs;
  R.periods = (n - P - s) / P; if (R.periods < 0) R.periods = 0; R.mism_after_s = mism;
  return R;
}
static const char *dirname(const res_t *r){ if (strcmp(r->outcome,"certified")) return "none";
  return r->dx>0 ? (r->dy>0 ? "+x,+y" : "+x,-y") : (r->dy>0 ? "-x,+y" : "-x,-y"); }

static void alloc(int64_t cap){
  CAPMAX = cap;
  grid = calloc((size_t)G*G, 1); dirty = malloc(sizeof(int32_t)*((size_t)cap + 2000000));
  T = malloc(cap+2); PX = malloc(2*(cap+2)); PY = malloc(2*(cap+2));
  BX0 = malloc(2*(cap+2)); BY0 = malloc(2*(cap+2)); BX1 = malloc(2*(cap+2)); BY1 = malloc(2*(cap+2));
  CX = malloc(2*1100*1100); CY = malloc(2*1100*1100);
  if (!grid||!dirty||!T||!PX||!PY||!BX0||!BY0||!BX1||!BY1) { fprintf(stderr,"alloc\n"); exit(1); }
}
static void print_json(FILE *f, int k, double p, uint64_t seed, uint64_t idx, const res_t *r, int cells){
  fprintf(f, "{\"k\": %d, \"p\": %g, \"seed\": %llu, \"sample_index\": %llu, \"outcome\": \"%s\", \"onset_step\": %lld, \"direction\": \"%s\", \"steps_simulated\": %lld, \"n_black\": %d, \"disp\": [%d,%d], \"final_pos\": [%d,%d], \"bbox_pre_onset\": [%d,%d,%d,%d], \"periods_verified\": %lld, \"max_abs_coord_all_steps\": %d, \"mismatches_after_s\": %d",
    k, p, (unsigned long long)seed, (unsigned long long)idx, r->outcome, (long long)r->s, dirname(r), (long long)r->n, r->nblack, r->dx, r->dy, r->fx, r->fy, r->bx0, r->by0, r->bx1, r->by1, (long long)r->periods, r->maxabs, r->mism_after_s);
  if (cells) { fprintf(f, ", \"black_cells\": ["); for (int i=0;i<ncell;i++) fprintf(f, "%s[%d,%d]", i?",":"", CX[i], CY[i]); fprintf(f, "]"); }
  fprintf(f, "}\n");
}

int main(int argc, char **argv){
  if (argc < 3) { fprintf(stderr, "usage\n"); return 1; }
  const char *mode = argv[1];
  if (!strcmp(mode, "cells")) {
    int64_t cap = atoll(argv[3]); alloc(cap);
    FILE *f = fopen(argv[2], "r"); if (!f) { perror("cells"); return 1; }
    ncell = 0; int a, b; while (fscanf(f, "%d %d", &a, &b) == 2) { CX[ncell]=a; CY[ncell]=b; ncell++; } fclose(f);
    res_t r = simulate(cap); print_json(stdout, 0, 0, 0, 0, &r, 0); return 0;
  }
  int k = atoi(argv[2]); double p = atof(argv[3]); uint64_t seed = strtoull(argv[4], 0, 10);
  if (!strcmp(mode, "dump")) { CX = malloc(2*1100*1100); CY = malloc(2*1100*1100); uint64_t idx = strtoull(argv[5],0,10); gen(k,p,seed,idx);
    printf("{\"k\": %d, \"p\": %g, \"seed\": %llu, \"sample_index\": %llu, \"n_black\": %d, \"black_cells\": [", k, p, (unsigned long long)seed, (unsigned long long)idx, ncell);
    for (int i=0;i<ncell;i++) printf("%s[%d,%d]", i?",":"", CX[i], CY[i]); printf("]}\n"); return 0; }
  if (!strcmp(mode, "long")) { /* long k p seed idx nsteps : no certification stop; post-hoc s over the whole run */
    uint64_t idx = strtoull(argv[5],0,10); int64_t cap = atoll(argv[6]); alloc(cap); gen(k,p,seed,idx); NOSTOP = 1;
    res_t r = simulate(cap); print_json(stdout, k, p, seed, idx, &r, 0); return 0; }
  if (!strcmp(mode, "one")) { uint64_t idx = strtoull(argv[5],0,10); int64_t cap = atoll(argv[6]); alloc(cap); gen(k,p,seed,idx);
    res_t r = simulate(cap); print_json(stdout, k, p, seed, idx, &r, 1); return 0; }
  uint64_t ns = strtoull(argv[5],0,10); int64_t cap = atoll(argv[6]); alloc(cap);
  if (!strcmp(mode, "run")) {
    FILE *fo = fopen(argv[7], "a");
    for (uint64_t idx = 0; idx < ns; idx++) { gen(k,p,seed,idx); res_t r = simulate(cap);
      fprintf(fo, "%d,%g,%llu,%llu,%s,%lld,\"%s\",%lld,%d,%d,%d,%d,%d,%d,%d,%d,%d,%lld,%d,%d\n", k, p, (unsigned long long)seed, (unsigned long long)idx,
        r.outcome, (long long)r.s, dirname(&r), (long long)r.n, r.nblack, r.dx, r.dy, r.fx, r.fy, r.bx0, r.by0, r.bx1, r.by1, (long long)r.periods, r.maxabs, r.mism_after_s); }
    fclose(fo); return 0;
  }
  if (!strcmp(mode, "u32")) {
    char fn[600]; snprintf(fn, sizeof fn, "%s.u32", argv[7]); FILE *fu = fopen(fn, "wb");
    snprintf(fn, sizeof fn, "%s_special.txt", argv[7]); FILE *fs = fopen(fn, "w");
    int64_t ncert=0, smax=-1, argmax=-1, tot=0; double ssum=0; int maxabs=0; int64_t maxn=0; int64_t dc[4]={0,0,0,0}; int64_t nd=0; double nb=0;
    for (uint64_t idx = 0; idx < ns; idx++) { gen(k,p,seed,idx); res_t r = simulate(cap); tot += r.n; nb += r.nblack;
      if (r.maxabs > maxabs) maxabs = r.maxabs; if (r.n > maxn) maxn = r.n;
      if (!strcmp(r.outcome,"certified")) { ncert++; ssum += r.s; uint32_t v = (uint32_t)r.s; fwrite(&v,4,1,fu); if (r.s > smax) { smax = r.s; argmax = idx; }
        dc[(r.dx>0?0:2)+(r.dy>0?0:1)]++; if (abs(r.dx)!=2 || abs(r.dy)!=2) nd++; }
      else print_json(fs, k, p, seed, idx, &r, 1); }
    fclose(fu); fclose(fs);
    snprintf(fn, sizeof fn, "%s_summary.jsonl", argv[7]); FILE *fj = fopen(fn, "a");
    fprintf(fj, "{\"k\": %d, \"p\": %g, \"seed\": %llu, \"n\": %llu, \"n_certified\": %lld, \"s_max\": %lld, \"argmax_sample_index\": %lld, \"s_mean\": %.6f, \"mean_n_black\": %.6f, \"dir_counts\": [%lld,%lld,%lld,%lld], \"n_disp_not_pm2_pm2\": %lld, \"total_steps\": %lld, \"max_steps_single_run\": %lld, \"max_abs_coord_all_steps\": %d}\n",
      k, p, (unsigned long long)seed, (unsigned long long)ns, (long long)ncert, (long long)smax, (long long)argmax, ncert? ssum/ncert : -1.0, nb/ns, (long long)dc[0],(long long)dc[1],(long long)dc[2],(long long)dc[3], (long long)nd, (long long)tot, (long long)maxn, maxabs);
    fclose(fj);
    fprintf(stderr, "u32 k=%d p=%g seed=%llu n=%llu cert=%lld smax=%lld idx=%lld maxabs=%d\n", k, p, (unsigned long long)seed, (unsigned long long)ns, (long long)ncert, (long long)smax, (long long)argmax, maxabs);
    return 0;
  }
  fprintf(stderr, "unknown mode\n"); return 1;
}
