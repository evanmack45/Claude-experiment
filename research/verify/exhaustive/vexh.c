/*
 * vexh.c -- INDEPENDENT re-implementation (verifier) of the exhaustive
 * Langton's-ant highway test, written from research/CONVENTIONS.md only.
 * Deliberately different design from research/exhaustive/exhaust.c:
 *   - 2048x2048 colour-only grid, reset by replaying the stored position history
 *   - FULL per-step arrays (turns, positions, prefix bounding boxes), no rings
 *   - after every certified run the onset step and the periodicity are
 *     re-verified LITERALLY from the stored turn sequence, and the onset
 *     bounding box is recomputed literally from the stored positions
 *   - an alternative certification step ("altcert") is computed with the
 *     bounding box that does NOT include unvisited initial black cells
 *     (literal reading of "cells modified before step s+1")
 *   - max |coordinate| is tracked over the WHOLE path, not only the final position
 *
 * Usage: ./vexh k lo hi cap outprefix
 * Writes <outprefix>.rec (16 bytes per config, see struct rec) and
 * <outprefix>.sum (text summary).
 *
 * Conventions: origin (0,0), facing North (0,+1); N->E->S->W is a right turn;
 * white -> right, black -> left; flip; move.  Config bit i <-> cell
 * (xmin + i % k, ymin + i / k), xmin = ymin = -(k/2).
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>

#define G 2048
#define OR 1024
#define LIM 1000
#define P 104
#define NPER 20
#define MARGIN 20
#define CERTLEN (P + NPER * P)  /* 2184 */

enum { CERT = 0, CAP = 1, BOUND = 2, NONTRAVEL = 3 };

struct rec { uint32_t s, cert, altcert; int8_t dx, dy, dir, status; };

static uint8_t *grid, *T;
static int16_t *PX, *PY, *BX0, *BY0, *BX1, *BY1;

static const int DX[4] = {0, 1, 0, -1};
static const int DY[4] = {1, 0, -1, 0};

int main(int argc, char **argv)
{
    if (argc < 6) { fprintf(stderr, "usage: %s k lo hi cap outprefix\n", argv[0]); return 1; }
    int k = atoi(argv[1]);
    uint64_t lo = strtoull(argv[2], 0, 10), hi = strtoull(argv[3], 0, 10);
    int64_t cap = atoll(argv[4]);
    const char *pre = argv[5];
    if (k < 1 || k > 5 || hi > (1ULL << (k * k))) { fprintf(stderr, "bad k/hi\n"); return 1; }
    int xmin = -(k / 2), ymin = -(k / 2);

    grid = calloc((size_t)G * G, 1);
    T = malloc(cap + P + 2);
    PX = malloc(sizeof(int16_t) * (cap + 2)); PY = malloc(sizeof(int16_t) * (cap + 2));
    BX0 = malloc(sizeof(int16_t) * (cap + 2)); BY0 = malloc(sizeof(int16_t) * (cap + 2));
    BX1 = malloc(sizeof(int16_t) * (cap + 2)); BY1 = malloc(sizeof(int16_t) * (cap + 2));
    if (!grid || !T || !PX || !PY || !BX0 || !BY0 || !BX1 || !BY1) { fprintf(stderr, "alloc\n"); return 1; }

    char fn[600];
    snprintf(fn, sizeof fn, "%s.rec", pre); FILE *frec = fopen(fn, "wb");
    if (!frec) { perror("rec"); return 1; }

    int64_t cnt[4] = {0, 0, 0, 0}, dircnt[4] = {0, 0, 0, 0};
    int64_t total_steps = 0, max_steps = 0, max_abs_final = 0, max_abs_path = 0;
    int64_t smin = -1, smax = -1; uint64_t argmin = 0, argmax = 0;
    int64_t n_altcert_differs = 0, n_disp_not_pm2 = 0, n_literal_fail = 0, n_bbox_mismatch = 0;
    int64_t altcert_diff_sum = 0;
    struct timespec t0, t1; clock_gettime(CLOCK_MONOTONIC, &t0);

    for (uint64_t cfg = lo; cfg < hi; cfg++) {
        /* initial configuration */
        int ibx0 = OR, iby0 = OR, ibx1 = OR, iby1 = OR;  /* origin included */
        int ncell = 0; int icx[32], icy[32];
        for (int i = 0; i < k * k; i++) if ((cfg >> i) & 1ULL) {
            int cx = OR + xmin + i % k, cy = OR + ymin + i / k;
            grid[cy * G + cx] = 1; icx[ncell] = cx; icy[ncell] = cy; ncell++;
            if (cx < ibx0) ibx0 = cx; if (cx > ibx1) ibx1 = cx;
            if (cy < iby0) iby0 = cy; if (cy > iby1) iby1 = cy;
        }
        int x = OR, y = OR, d = 0;
        int bx0 = ibx0, by0 = iby0, bx1 = ibx1, by1 = iby1;
        PX[0] = x; PY[0] = y; BX0[0] = bx0; BY0[0] = by0; BX1[0] = bx1; BY1[0] = by1;
        int64_t n = 0, L = 0; int status = CAP, dx = 0, dy = 0;
        while (n < cap) {
            n++;
            int idx = y * G + x; uint8_t c = grid[idx]; uint8_t t;
            if (c) { d = (d + 3) & 3; t = 0; } else { d = (d + 1) & 3; t = 1; }
            grid[idx] = c ^ 1;
            if (x < bx0) bx0 = x; if (x > bx1) bx1 = x;
            if (y < by0) by0 = y; if (y > by1) by1 = y;
            x += DX[d]; y += DY[d];
            T[n] = t; PX[n] = x; PY[n] = y; BX0[n] = bx0; BY0[n] = by0; BX1[n] = bx1; BY1[n] = by1;
            if (x - OR >= LIM || OR - x >= LIM || y - OR >= LIM || OR - y >= LIM) { status = BOUND; break; }
            if (n > P && T[n] != T[n - P]) L = n - P;
            if (n >= L + CERTLEN) {
                dx = PX[n] - PX[n - P]; dy = PY[n] - PY[n - P];
                if (dx != 0 && dy != 0) {
                    int sx0 = BX0[L], sy0 = BY0[L], sx1 = BX1[L], sy1 = BY1[L];
                    int okx = dx > 0 ? (x >= sx1 + MARGIN) : (x <= sx0 - MARGIN);
                    int oky = dy > 0 ? (y >= sy1 + MARGIN) : (y <= sy0 - MARGIN);
                    if (okx && oky) { status = CERT; break; }
                }
            }
        }
        if (status == CAP && n >= L + CERTLEN) status = NONTRAVEL;

        struct rec r; memset(&r, 0, sizeof r);
        r.s = (uint32_t)L; r.cert = (uint32_t)n; r.altcert = 0; r.dx = (int8_t)dx; r.dy = (int8_t)dy;
        r.dir = (int8_t)((dx > 0 ? 0 : 2) + (dy > 0 ? 0 : 1)); r.status = (int8_t)status;
        total_steps += n; if (n > max_steps) max_steps = n;
        { int64_t a = abs(x - OR), b = abs(y - OR); if (b > a) a = b; if (a > max_abs_final) max_abs_final = a;
          int64_t m[4] = {OR - bx0, bx1 - OR, OR - by0, by1 - OR};
          for (int i = 0; i < 4; i++) if (m[i] > max_abs_path) max_abs_path = m[i];
          if (a > max_abs_path) max_abs_path = a; }
        cnt[status]++;
        if (status == CERT) {
            dircnt[r.dir]++;
            if (abs(dx) != 2 || abs(dy) != 2) n_disp_not_pm2++;
            if (smin < 0 || L < smin) { smin = L; argmin = cfg; }
            if (smax < 0 || L > smax) { smax = L; argmax = cfg; }
            /* LITERAL re-verification from the stored turn sequence */
            int ok = 1;
            for (int64_t q = L + 1; q + P <= n; q++) if (T[q] != T[q + P]) { ok = 0; break; }
            if (L >= 1 && T[L] == T[L + P]) ok = 0;
            if ((n - P) - L < NPER * P) ok = 0;
            if (!ok) n_literal_fail++;
            /* literal bbox of cells modified in steps 1..L (positions before steps 1..L = PX[0..L-1]) */
            int lx0 = OR, ly0 = OR, lx1 = OR, ly1 = OR;   /* origin */
            for (int64_t q = 0; q < L; q++) {
                if (PX[q] < lx0) lx0 = PX[q]; if (PX[q] > lx1) lx1 = PX[q];
                if (PY[q] < ly0) ly0 = PY[q]; if (PY[q] > ly1) ly1 = PY[q];
            }
            /* alt certification step: bbox WITHOUT unvisited initial black cells */
            int64_t ac = 0;
            for (int64_t q = L + CERTLEN; q <= n; q++) {
                int ddx = PX[q] - PX[q - P], ddy = PY[q] - PY[q - P];
                if (ddx == 0 || ddy == 0) continue;
                int okx = ddx > 0 ? (PX[q] >= lx1 + MARGIN) : (PX[q] <= lx0 - MARGIN);
                int oky = ddy > 0 ? (PY[q] >= ly1 + MARGIN) : (PY[q] <= ly0 - MARGIN);
                if (okx && oky) { ac = q; break; }
            }
            r.altcert = (uint32_t)ac;
            if (ac != n) { n_altcert_differs++; altcert_diff_sum += n - ac; }
            /* bbox with initial cells must equal the prefix-array snapshot */
            int fx0 = lx0, fy0 = ly0, fx1 = lx1, fy1 = ly1;
            for (int i = 0; i < ncell; i++) {
                if (icx[i] < fx0) fx0 = icx[i]; if (icx[i] > fx1) fx1 = icx[i];
                if (icy[i] < fy0) fy0 = icy[i]; if (icy[i] > fy1) fy1 = icy[i];
            }
            if (fx0 != BX0[L] || fy0 != BY0[L] || fx1 != BX1[L] || fy1 != BY1[L]) n_bbox_mismatch++;
        }
        fwrite(&r, sizeof r, 1, frec);
        /* reset grid by replaying history */
        for (int64_t q = 0; q < n; q++) grid[PY[q] * G + PX[q]] = 0;
        for (int i = 0; i < ncell; i++) grid[icy[i] * G + icx[i]] = 0;

        if (((cfg - lo + 1) & 0x3FFFFF) == 0) {
            clock_gettime(CLOCK_MONOTONIC, &t1);
            double el = (t1.tv_sec - t0.tv_sec) + 1e-9 * (t1.tv_nsec - t0.tv_nsec);
            fprintf(stderr, "[%s] %llu/%llu %.0fs %.1f Msteps/s cert=%lld cap=%lld bound=%lld nt=%lld smax=%lld\n", pre,
                (unsigned long long)(cfg - lo + 1), (unsigned long long)(hi - lo), el, total_steps / el / 1e6,
                (long long)cnt[0], (long long)cnt[1], (long long)cnt[2], (long long)cnt[3], (long long)smax);
        }
    }
    fclose(frec);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double el = (t1.tv_sec - t0.tv_sec) + 1e-9 * (t1.tv_nsec - t0.tv_nsec);
    snprintf(fn, sizeof fn, "%s.sum", pre); FILE *fs = fopen(fn, "w");
    fprintf(fs, "{\"k\": %d, \"lo\": %llu, \"hi\": %llu, \"cap\": %lld, \"n_configs\": %llu,\n"
        "\"n_cert\": %lld, \"n_cap\": %lld, \"n_bound\": %lld, \"n_nontravel\": %lld,\n"
        "\"s_min\": %lld, \"argmin_cfg\": %llu, \"s_max\": %lld, \"argmax_cfg\": %llu,\n"
        "\"dir_counts\": [%lld, %lld, %lld, %lld],\n"
        "\"total_steps\": %lld, \"max_steps\": %lld, \"max_abs_final_pos\": %lld, \"max_abs_any_cell_on_path\": %lld,\n"
        "\"n_disp_not_pm2\": %lld, \"n_literal_recheck_failures\": %lld, \"n_bbox_mismatch\": %lld,\n"
        "\"n_altcert_differs\": %lld, \"altcert_diff_sum\": %lld, \"elapsed_s\": %.3f, \"msteps_per_s\": %.2f}\n",
        k, (unsigned long long)lo, (unsigned long long)hi, (long long)cap, (unsigned long long)(hi - lo),
        (long long)cnt[0], (long long)cnt[1], (long long)cnt[2], (long long)cnt[3],
        (long long)smin, (unsigned long long)argmin, (long long)smax, (unsigned long long)argmax,
        (long long)dircnt[0], (long long)dircnt[1], (long long)dircnt[2], (long long)dircnt[3],
        (long long)total_steps, (long long)max_steps, (long long)max_abs_final, (long long)max_abs_path,
        (long long)n_disp_not_pm2, (long long)n_literal_fail, (long long)n_bbox_mismatch,
        (long long)n_altcert_differs, (long long)altcert_diff_sum, el, total_steps / el / 1e6);
    fclose(fs);
    fprintf(stderr, "[%s] done %.1fs %.1f Msteps/s\n", pre, el, total_steps / el / 1e6);
    return 0;
}
