/*
 * exhaust.c -- exhaustive Langton's-ant highway test over all 2^(k*k)
 * initial configurations in a k x k box (research/CONVENTIONS.md).
 *
 * Usage: ./exhaust k lo hi cap outprefix [records]
 *   k         box size (1..5)
 *   lo, hi    configuration index range [lo, hi) (hi <= 2^(k*k))
 *   cap       step cap per configuration
 *   outprefix output files: <outprefix>_summary.txt, <outprefix>_hist.bin
 *             (uint32 counts of onset step s over certified runs, index 0..cap),
 *             <outprefix>_special.txt (cap/boundary/non-traveling runs),
 *             and if records=1, <outprefix>_records.csv (one line per config).
 *
 * Configuration encoding: bit i (i = 0 .. k*k-1) of the index is the colour of
 * cell (x, y) = (xmin + i % k, ymin + i / k) with xmin = ymin = -(k/2)
 * (integer division), i.e. -floor(k/2) for odd k and -k/2 for even k, which is
 * exactly the box of CONVENTIONS.md. Bit set = black.
 *
 * Conventions: ant at origin facing N=(0,+1); white -> turn right (clockwise
 * N->E), black -> turn left; flip; move. t[n]='R' if step n turned right.
 *
 * Onset step s = max { k : t[k] != t[k+104] } (0 if no mismatch). We keep a
 * 128-entry ring of the last turns and compare t[n] with t[n-104]; on a
 * mismatch at step n we set L = n-104 and snapshot the bounding box of all
 * cells modified in steps 1..L (plus the initial black cells and the origin)
 * from a parallel ring of per-step bounding boxes.
 *
 * Certification (sound, per CONVENTIONS.md): at step n with n >= L + 2184 the
 * equalities t[k] == t[k+104] have been verified for every k in L+1 .. n-104,
 * i.e. for at least 2080 = 20*104 consecutive indices (20 full periods).
 * Additionally the ant's current position must be beyond the snapshot bounding
 * box by >= 20 cells in BOTH coordinates in the direction of travel, where the
 * direction of travel is the sign of the displacement over the last period
 * (pos(n) - pos(n-104)). Both components of that displacement must be nonzero.
 * When both conditions hold the run is certified and stopped.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>

#define GRID 4096
#define ORIGIN (GRID/2)
#define RING 128
#define RMASK (RING-1)
#define PERIOD 104
#define NPERIODS 20
#define MARGIN 20
#define CERT_LEN (PERIOD + NPERIODS*PERIOD)   /* 2184 */

enum { ST_CERT = 0, ST_CAP = 1, ST_BOUNDARY = 2, ST_NONTRAVEL = 3 };

static uint8_t *cells;      /* bit0 = colour, bit1 = touched */
static int32_t *touched;    /* indices of touched cells for fast reset */
static long ntouched;

typedef struct {
    int status;
    int64_t s;          /* onset step */
    int64_t steps;      /* steps executed when the run stopped */
    int dispx, dispy;   /* displacement per period at certification */
    int fx, fy;         /* final ant position (relative to origin) */
    int bx0, by0, bx1, by1;  /* bounding box at onset (relative to origin) */
    int dirid;          /* 0:+x,+y 1:+x,-y 2:-x,+y 3:-x,-y */
} result_t;

static const char *DIRNAME[4] = {"+x,+y", "+x,-y", "-x,+y", "-x,-y"};

static void run(int k, uint64_t cfg, int64_t cap, result_t *r)
{
    static const int DX[4] = {0, 1, 0, -1};
    static const int DY[4] = {1, 0, -1, 0};
    int xmin = -(k / 2), ymin = -(k / 2);
    int bx0 = ORIGIN, by0 = ORIGIN, bx1 = ORIGIN, by1 = ORIGIN; /* includes origin */
    ntouched = 0;
    for (int i = 0; i < k * k; i++) {
        if ((cfg >> i) & 1ULL) {
            int cx = ORIGIN + xmin + i % k, cy = ORIGIN + ymin + i / k;
            int32_t idx = cy * GRID + cx;
            cells[idx] = 3;
            touched[ntouched++] = idx;
            if (cx < bx0) bx0 = cx; if (cx > bx1) bx1 = cx;
            if (cy < by0) by0 = cy; if (cy > by1) by1 = cy;
        }
    }
    uint8_t tring[RING];
    int32_t rbx0[RING], rby0[RING], rbx1[RING], rby1[RING], rpx[RING], rpy[RING];
    int x = ORIGIN, y = ORIGIN, dir = 0;
    /* state after step 0 */
    rbx0[0] = bx0; rby0[0] = by0; rbx1[0] = bx1; rby1[0] = by1; rpx[0] = x; rpy[0] = y;
    int sbx0 = bx0, sby0 = by0, sbx1 = bx1, sby1 = by1; /* snapshot bbox at step L */
    int64_t L = 0, n = 0;
    int status = ST_CAP, dispx = 0, dispy = 0;

    while (n < cap) {
        n++;
        int32_t idx = y * GRID + x;
        uint8_t c = cells[idx];
        uint8_t t;
        if (c & 1) { dir = (dir + 3) & 3; t = 0; }   /* black: left */
        else       { dir = (dir + 1) & 3; t = 1; }   /* white: right */
        if (!(c & 2)) touched[ntouched++] = idx;
        cells[idx] = (uint8_t)(2 | ((c & 1) ^ 1));
        if (x < bx0) bx0 = x; else if (x > bx1) bx1 = x;
        if (y < by0) by0 = y; else if (y > by1) by1 = y;
        x += DX[dir]; y += DY[dir];
        if (x <= 0 || x >= GRID - 1 || y <= 0 || y >= GRID - 1) { status = ST_BOUNDARY; break; }
        int ri = (int)(n & RMASK);
        if (n > PERIOD) {
            int pi = (int)((n - PERIOD) & RMASK);
            if (tring[pi] != t) {
                L = n - PERIOD;
                sbx0 = rbx0[pi]; sby0 = rby0[pi]; sbx1 = rbx1[pi]; sby1 = rby1[pi];
            }
        }
        tring[ri] = t;
        rbx0[ri] = bx0; rby0[ri] = by0; rbx1[ri] = bx1; rby1[ri] = by1;
        rpx[ri] = x; rpy[ri] = y;
        if (n >= L + CERT_LEN) {
            int pi = (int)((n - PERIOD) & RMASK);
            dispx = x - rpx[pi]; dispy = y - rpy[pi];
            if (dispx != 0 && dispy != 0) {
                int okx = dispx > 0 ? (x >= sbx1 + MARGIN) : (x <= sbx0 - MARGIN);
                int oky = dispy > 0 ? (y >= sby1 + MARGIN) : (y <= sby0 - MARGIN);
                if (okx && oky) { status = ST_CERT; break; }
            }
        }
    }
    if (status == ST_CAP && n >= L + CERT_LEN) status = ST_NONTRAVEL;
    /* fast reset */
    for (long i = 0; i < ntouched; i++) cells[touched[i]] = 0;

    r->status = status; r->s = L; r->steps = n;
    r->dispx = dispx; r->dispy = dispy;
    r->fx = x - ORIGIN; r->fy = y - ORIGIN;
    r->bx0 = sbx0 - ORIGIN; r->by0 = sby0 - ORIGIN; r->bx1 = sbx1 - ORIGIN; r->by1 = sby1 - ORIGIN;
    r->dirid = (dispx > 0 ? 0 : 2) + (dispy > 0 ? 0 : 1);
}

static void print_cells(FILE *f, int k, uint64_t cfg)
{
    int xmin = -(k / 2), ymin = -(k / 2), first = 1;
    fputc('[', f);
    for (int i = 0; i < k * k; i++) if ((cfg >> i) & 1ULL) {
        fprintf(f, "%s[%d,%d]", first ? "" : ",", xmin + i % k, ymin + i / k);
        first = 0;
    }
    fputc(']', f);
}

int main(int argc, char **argv)
{
    if (argc < 6) { fprintf(stderr, "usage: %s k lo hi cap outprefix [records]\n", argv[0]); return 1; }
    int k = atoi(argv[1]);
    uint64_t lo = strtoull(argv[2], 0, 10), hi = strtoull(argv[3], 0, 10);
    int64_t cap = atoll(argv[4]);
    const char *pre = argv[5];
    int records = argc > 6 ? atoi(argv[6]) : 0;
    if (k < 1 || k > 5) { fprintf(stderr, "k must be 1..5\n"); return 1; }
    uint64_t total = 1ULL << (k * k);
    if (hi > total) hi = total;

    cells = calloc((size_t)GRID * GRID, 1);
    touched = malloc(sizeof(int32_t) * (size_t)(cap + k * k + 8));
    uint32_t *hist = calloc((size_t)cap + 1, sizeof(uint32_t));
    if (!cells || !touched || !hist) { fprintf(stderr, "alloc failed\n"); return 1; }

    char fn[512];
    FILE *frec = NULL, *fspec, *fsum, *fhist;
    if (records) { snprintf(fn, sizeof fn, "%s_records.csv", pre); frec = fopen(fn, "w");
        fprintf(frec, "cfg,status,s,steps,dispx,dispy,dir,fx,fy,bx0,by0,bx1,by1,cells\n"); }
    snprintf(fn, sizeof fn, "%s_special.txt", pre); fspec = fopen(fn, "w");

    int64_t ncert = 0, ncap = 0, nbound = 0, nnontr = 0;
    int64_t smin = -1, smax = -1; uint64_t argmax = 0, argmin = 0; result_t rmax = {0}, rmin = {0};
    double ssum = 0; int64_t dircount[4] = {0, 0, 0, 0};
    int64_t total_steps = 0, max_cert_steps = 0, max_abs_coord = 0, n_disp_not_2_2 = 0;
    struct timespec t0, t1; clock_gettime(CLOCK_MONOTONIC, &t0);

    for (uint64_t cfg = lo; cfg < hi; cfg++) {
        result_t r; run(k, cfg, cap, &r);
        total_steps += r.steps;
        int64_t ac = llabs(r.fx) > llabs(r.fy) ? llabs(r.fx) : llabs(r.fy);
        if (ac > max_abs_coord) max_abs_coord = ac;
        if (r.status == ST_CERT) {
            ncert++; hist[r.s]++; ssum += (double)r.s; dircount[r.dirid]++;
            if (abs(r.dispx) != 2 || abs(r.dispy) != 2) n_disp_not_2_2++;
            if (r.steps > max_cert_steps) max_cert_steps = r.steps;
            if (smax < 0 || r.s > smax) { smax = r.s; argmax = cfg; rmax = r; }
            if (smin < 0 || r.s < smin) { smin = r.s; argmin = cfg; rmin = r; }
        } else {
            if (r.status == ST_CAP) ncap++; else if (r.status == ST_BOUNDARY) nbound++; else nnontr++;
            fprintf(fspec, "cfg=%llu status=%d s=%lld steps=%lld fx=%d fy=%d cells=",
                    (unsigned long long)cfg, r.status, (long long)r.s, (long long)r.steps, r.fx, r.fy);
            print_cells(fspec, k, cfg); fputc('\n', fspec); fflush(fspec);
        }
        if (frec) {
            fprintf(frec, "%llu,%d,%lld,%lld,%d,%d,\"%s\",%d,%d,%d,%d,%d,%d,\"",
                    (unsigned long long)cfg, r.status, (long long)r.s, (long long)r.steps,
                    r.dispx, r.dispy, r.status == ST_CERT ? DIRNAME[r.dirid] : "none",
                    r.fx, r.fy, r.bx0, r.by0, r.bx1, r.by1);
            print_cells(frec, k, cfg); fprintf(frec, "\"\n");
        }
        if (((cfg - lo + 1) & 0xFFFFF) == 0) {
            clock_gettime(CLOCK_MONOTONIC, &t1);
            double el = (t1.tv_sec - t0.tv_sec) + 1e-9 * (t1.tv_nsec - t0.tv_nsec);
            fprintf(stderr, "[%s] %llu/%llu done, %.1fs, %.1f Msteps/s, cap=%lld bound=%lld\n", pre,
                    (unsigned long long)(cfg - lo + 1), (unsigned long long)(hi - lo), el,
                    total_steps / el / 1e6, (long long)ncap, (long long)nbound);
        }
    }
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double el = (t1.tv_sec - t0.tv_sec) + 1e-9 * (t1.tv_nsec - t0.tv_nsec);

    snprintf(fn, sizeof fn, "%s_hist.bin", pre); fhist = fopen(fn, "wb");
    fwrite(hist, sizeof(uint32_t), (size_t)cap + 1, fhist); fclose(fhist);

    snprintf(fn, sizeof fn, "%s_summary.txt", pre); fsum = fopen(fn, "w");
    fprintf(fsum, "{\n\"k\": %d, \"lo\": %llu, \"hi\": %llu, \"cap\": %lld, \"grid\": %d,\n",
            k, (unsigned long long)lo, (unsigned long long)hi, (long long)cap, GRID);
    fprintf(fsum, "\"n_configs\": %llu, \"n_certified\": %lld, \"n_cap\": %lld, \"n_boundary\": %lld, \"n_nontraveling_periodic\": %lld,\n",
            (unsigned long long)(hi - lo), (long long)ncert, (long long)ncap, (long long)nbound, (long long)nnontr);
    fprintf(fsum, "\"s_min\": %lld, \"s_max\": %lld, \"s_sum\": %.0f,\n", (long long)smin, (long long)smax, ssum);
    fprintf(fsum, "\"argmax_cfg\": %llu, \"argmax_cells\": ", (unsigned long long)argmax); print_cells(fsum, k, argmax);
    fprintf(fsum, ", \"argmax_dir\": \"%s\", \"argmax_disp\": [%d,%d], \"argmax_cert_step\": %lld, \"argmax_bbox\": [%d,%d,%d,%d],\n",
            DIRNAME[rmax.dirid], rmax.dispx, rmax.dispy, (long long)rmax.steps, rmax.bx0, rmax.by0, rmax.bx1, rmax.by1);
    fprintf(fsum, "\"argmin_cfg\": %llu, \"argmin_cells\": ", (unsigned long long)argmin); print_cells(fsum, k, argmin);
    fprintf(fsum, ", \"argmin_dir\": \"%s\",\n", DIRNAME[rmin.dirid]);
    fprintf(fsum, "\"dir_counts\": {\"+x,+y\": %lld, \"+x,-y\": %lld, \"-x,+y\": %lld, \"-x,-y\": %lld},\n",
            (long long)dircount[0], (long long)dircount[1], (long long)dircount[2], (long long)dircount[3]);
    fprintf(fsum, "\"n_disp_not_2_2\": %lld,\n", (long long)n_disp_not_2_2);
    fprintf(fsum, "\"total_steps\": %lld, \"elapsed_s\": %.3f, \"msteps_per_s\": %.2f, \"max_cert_steps\": %lld, \"max_abs_coord\": %lld\n}\n",
            (long long)total_steps, el, total_steps / el / 1e6, (long long)max_cert_steps, (long long)max_abs_coord);
    fclose(fsum); fclose(fspec); if (frec) fclose(frec);
    fprintf(stderr, "[%s] finished: %llu configs, %.1fs, %.1f Msteps/s, cert=%lld cap=%lld bound=%lld nontravel=%lld smax=%lld\n",
            pre, (unsigned long long)(hi - lo), el, total_steps / el / 1e6,
            (long long)ncert, (long long)ncap, (long long)nbound, (long long)nnontr, (long long)smax);
    return 0;
}
