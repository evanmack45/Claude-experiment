/*
 * antsim.c -- Langton's-ant simulator with certified highway detection,
 * written for research/adversarial (see research/CONVENTIONS.md).
 *
 * Usage:
 *   ./antsim run   <cfgfile> [--cap N] [--grid G] [--log-every M] [--dump-final F]
 *   ./antsim batch           [--cap N] [--grid G]       (one configuration per stdin line)
 *
 * Configuration file: the black cells as integer pairs "x y" (one per line,
 * '#' comments allowed) OR a JSON array [[x,y],...].  Any non-integer
 * characters are ignored, so both forms parse.  An empty file = empty grid.
 * In batch mode each stdin line is one configuration in the same free form
 * (e.g. "x,y x,y ..."); an empty line is the empty grid.  One JSON result
 * line is printed per configuration.
 *
 * Conventions (CONVENTIONS.md): x East, y North; ant starts at (0,0) facing N;
 * white -> turn right (N->E), black -> turn left; flip; move.
 * t[k] = 'R' if step k turned right.
 * Onset step s = max{k >= 1 : t[k] != t[k+104]} (0 if no mismatch ever), i.e.
 * the smallest s with t[k] == t[k+104] for every k >= s+1.
 *
 * Certification (identical rule to research/exhaustive and research/random):
 * at step n >= s + 2184, t[k]==t[k+104] has been verified for every k in
 * s+1..n-104 (>= 20 full periods = 2080 indices), AND the ant is >= 20 cells
 * beyond the bounding box of {origin, initial black cells, cells modified in
 * steps 1..s} in BOTH coordinates in the direction of travel (sign of
 * pos(n) - pos(n-104), both components required nonzero).  The run then stops
 * with outcome "certified" and the certification step n is reported.
 *
 * Outcomes: certified | cap | boundary | nontravel
 *   cap        : cap reached, turns not 104-periodic for >= 20 periods
 *   boundary   : ant reached the outermost ring of the G x G grid (never wrapped)
 *   nontravel  : cap reached while turns were 104-periodic for >= 20 periods but
 *                the displacement had a zero component / escape margin not reached
 *
 * Extra reported fields:
 *   first_initial_black_read : first step k at which the ant read a cell that was
 *                              black in the initial configuration (0 = never)
 *   bbox_all                 : bounding box of everything modified during the run
 *   n_black_final, n_touched : black cells / distinct cells modified at stop
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <ctype.h>
#include <limits.h>
#include <time.h>

#define RING 128
#define RMASK (RING-1)
#define PERIOD 104
#define NPERIODS 20
#define MARGIN 20
#define CERT_LEN (PERIOD + NPERIODS*PERIOD)   /* 2184 */

enum { ST_CERT = 0, ST_CAP = 1, ST_BOUNDARY = 2, ST_NONTRAVEL = 3 };
static const char *STNAME[4] = {"certified", "cap", "boundary", "nontravel"};
static const char *DIRNAME[4] = {"+x,+y", "+x,-y", "-x,+y", "-x,-y"};

static int64_t G = 8192;           /* grid side */
static int64_t ORIGIN;
static uint8_t *cells;             /* bit0 colour, bit1 touched, bit2 initially black */
static int64_t *touched;           /* indices of touched cells (batch reset) */
static int64_t ntouched, touched_cap;
static inline void push_touched(int64_t idx) {
    if (ntouched == touched_cap) { touched_cap *= 2; touched = realloc(touched, sizeof(int64_t) * touched_cap); if (!touched) { fprintf(stderr, "realloc failed\n"); exit(3); } }
    touched[ntouched++] = idx;
}
static int64_t log_every = 0;
static FILE *logf;

typedef struct {
    int status;
    int64_t s, steps, cert_step, first_black_read;
    int dispx, dispy, fx, fy, dirid;
    int bx0, by0, bx1, by1;        /* pre-onset bbox (relative to origin) */
    int ax0, ay0, ax1, ay1;        /* bbox of everything touched */
    int nblack_init;
    int64_t nblack_final, ntouched_final, periods_verified;
    int dir_final;
} result_t;

/* ---- configuration parsing: extract all integers from a string ---- */
static int parse_ints(const char *s, long **out) {
    int cap = 64, n = 0; long *v = malloc(sizeof(long) * cap);
    const char *p = s;
    while (*p) {
        if (isdigit((unsigned char)*p) || ((*p == '-' || *p == '+') && isdigit((unsigned char)p[1]))) {
            char *e; long val = strtol(p, &e, 10);
            if (n == cap) { cap *= 2; v = realloc(v, sizeof(long) * cap); }
            v[n++] = val; p = e;
        } else p++;
    }
    *out = v; return n;
}

static void run(const long *cfg, int ncells, int64_t cap, result_t *r)
{
    static const int DX[4] = {0, 1, 0, -1};
    static const int DY[4] = {1, 0, -1, 0};
    int64_t bx0 = ORIGIN, by0 = ORIGIN, bx1 = ORIGIN, by1 = ORIGIN;
    ntouched = 0;
    int nblack = 0;
    for (int i = 0; i < ncells; i++) {
        int64_t cx = ORIGIN + cfg[2*i], cy = ORIGIN + cfg[2*i+1];
        if (cx < 1 || cx >= G-1 || cy < 1 || cy >= G-1) { fprintf(stderr, "initial cell outside grid\n"); exit(2); }
        int64_t idx = cy * G + cx;
        if (cells[idx] & 1) continue;          /* duplicate */
        cells[idx] = 1 | 2 | 4;
        push_touched(idx);
        nblack++;
        if (cx < bx0) bx0 = cx;
        if (cx > bx1) bx1 = cx;
        if (cy < by0) by0 = cy;
        if (cy > by1) by1 = cy;
    }
    uint8_t tring[RING];
    int64_t rbx0[RING], rby0[RING], rbx1[RING], rby1[RING], rpx[RING], rpy[RING];
    int64_t x = ORIGIN, y = ORIGIN; int dir = 0;
    rbx0[0] = bx0; rby0[0] = by0; rbx1[0] = bx1; rby1[0] = by1; rpx[0] = x; rpy[0] = y;
    int64_t sbx0 = bx0, sby0 = by0, sbx1 = bx1, sby1 = by1;
    int64_t L = 0, n = 0, firstblack = 0, nb = nblack;
    int status = ST_CAP, dispx = 0, dispy = 0;

    while (n < cap) {
        n++;
        int64_t idx = y * G + x;
        uint8_t c = cells[idx];
        uint8_t t;
        if (c & 1) { dir = (dir + 3) & 3; t = 0; nb--; if ((c & 4) && !firstblack) firstblack = n; }
        else       { dir = (dir + 1) & 3; t = 1; nb++; }
        if (!(c & 2)) push_touched(idx);
        cells[idx] = (uint8_t)((c & 4) | 2 | ((c & 1) ^ 1));
        if (x < bx0) bx0 = x; else if (x > bx1) bx1 = x;
        if (y < by0) by0 = y; else if (y > by1) by1 = y;
        x += DX[dir]; y += DY[dir];
        if (x <= 0 || x >= G - 1 || y <= 0 || y >= G - 1) { status = ST_BOUNDARY; break; }
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
            dispx = (int)(x - rpx[pi]); dispy = (int)(y - rpy[pi]);
            if (dispx != 0 && dispy != 0) {
                int okx = dispx > 0 ? (x >= sbx1 + MARGIN) : (x <= sbx0 - MARGIN);
                int oky = dispy > 0 ? (y >= sby1 + MARGIN) : (y <= sby0 - MARGIN);
                if (okx && oky) { status = ST_CERT; break; }
            }
        }
        if (log_every && (n % log_every) == 0) {
            fprintf(logf, "{\"step\": %lld, \"pos\": [%lld,%lld], \"dir\": %d, \"bbox_all\": [%lld,%lld,%lld,%lld], "
                          "\"n_black\": %lld, \"n_touched\": %lld, \"last_mismatch_step\": %lld}\n",
                    (long long)n, (long long)(x-ORIGIN), (long long)(y-ORIGIN), dir,
                    (long long)(bx0-ORIGIN), (long long)(by0-ORIGIN), (long long)(bx1-ORIGIN), (long long)(by1-ORIGIN),
                    (long long)nb, (long long)ntouched, (long long)L);
            fflush(logf);
        }
    }
    if (status == ST_CAP && n >= L + CERT_LEN) status = ST_NONTRAVEL;

    r->status = status; r->s = L; r->steps = n; r->cert_step = (status == ST_CERT) ? n : -1;
    r->first_black_read = firstblack;
    r->dispx = dispx; r->dispy = dispy;
    r->fx = (int)(x - ORIGIN); r->fy = (int)(y - ORIGIN); r->dir_final = dir;
    r->bx0 = (int)(sbx0 - ORIGIN); r->by0 = (int)(sby0 - ORIGIN); r->bx1 = (int)(sbx1 - ORIGIN); r->by1 = (int)(sby1 - ORIGIN);
    r->ax0 = (int)(bx0 - ORIGIN); r->ay0 = (int)(by0 - ORIGIN); r->ax1 = (int)(bx1 - ORIGIN); r->ay1 = (int)(by1 - ORIGIN);
    r->dirid = (dispx > 0 ? 0 : 2) + (dispy > 0 ? 0 : 1);
    r->nblack_init = nblack; r->nblack_final = nb; r->ntouched_final = ntouched;
    r->periods_verified = (n - PERIOD - L) / PERIOD; if (r->periods_verified < 0) r->periods_verified = 0;
}

static void reset_grid(void) { for (int64_t i = 0; i < ntouched; i++) cells[touched[i]] = 0; ntouched = 0; }

static void dump_final(const char *fn) {
    /* write every black cell at stop as "x y" lines */
    FILE *f = fopen(fn, "w"); if (!f) return;
    for (int64_t i = 0; i < ntouched; i++) if (cells[touched[i]] & 1) {
        int64_t idx = touched[i]; fprintf(f, "%lld %lld\n", (long long)(idx % G - ORIGIN), (long long)(idx / G - ORIGIN));
    }
    fclose(f);
}

static void print_result(FILE *f, const result_t *r, int64_t cap) {
    fprintf(f, "{\"outcome\": \"%s\", \"onset_step\": %lld, \"direction\": \"%s\", \"period\": %d, \"disp\": [%d,%d], "
               "\"steps_simulated\": %lld, \"cert_step\": %lld, \"periods_verified\": %lld, \"cap\": %lld, \"grid\": %lld, "
               "\"n_black_init\": %d, \"first_initial_black_read\": %lld, \"final_pos\": [%d,%d], \"final_dir\": \"%c\", "
               "\"bbox_pre_onset\": [%d,%d,%d,%d], \"bbox_all\": [%d,%d,%d,%d], \"n_black_final\": %lld, \"n_touched\": %lld}\n",
            STNAME[r->status], (long long)r->s, r->status == ST_CERT ? DIRNAME[r->dirid] : "none", PERIOD, r->dispx, r->dispy,
            (long long)r->steps, (long long)r->cert_step, (long long)r->periods_verified, (long long)cap, (long long)G,
            r->nblack_init, (long long)r->first_black_read, r->fx, r->fy, "NESW"[r->dir_final],
            r->bx0, r->by0, r->bx1, r->by1, r->ax0, r->ay0, r->ax1, r->ay1, (long long)r->nblack_final, (long long)r->ntouched_final);
    fflush(f);
}

int main(int argc, char **argv)
{
    if (argc < 2) { fprintf(stderr, "usage: %s run <cfgfile> [--cap N] [--grid G] [--log-every M] [--dump-final F] | batch [--cap N] [--grid G]\n", argv[0]); return 1; }
    const char *mode = argv[1];
    int64_t cap = 50000000; const char *cfgfile = NULL, *dumpfn = NULL;
    for (int i = 2; i < argc; i++) {
        if (!strcmp(argv[i], "--cap") && i+1 < argc) cap = atoll(argv[++i]);
        else if (!strcmp(argv[i], "--grid") && i+1 < argc) G = atoll(argv[++i]);
        else if (!strcmp(argv[i], "--log-every") && i+1 < argc) log_every = atoll(argv[++i]);
        else if (!strcmp(argv[i], "--dump-final") && i+1 < argc) dumpfn = argv[++i];
        else if (!cfgfile) cfgfile = argv[i];
        else { fprintf(stderr, "bad arg %s\n", argv[i]); return 1; }
    }
    ORIGIN = G / 2; logf = stderr;
    cells = calloc((size_t)G * G, 1);
    touched_cap = 1 << 20; touched = malloc(sizeof(int64_t) * touched_cap);   /* grows by doubling */
    if (!cells || !touched) { fprintf(stderr, "alloc failed for grid %lld\n", (long long)G); return 1; }

    if (!strcmp(mode, "run")) {
        if (!cfgfile) { fprintf(stderr, "need cfgfile\n"); return 1; }
        FILE *f = fopen(cfgfile, "r"); if (!f) { fprintf(stderr, "cannot open %s\n", cfgfile); return 1; }
        fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
        char *buf = malloc(sz + 1); size_t rd = fread(buf, 1, sz, f); buf[rd] = 0; fclose(f);
        /* strip comments */
        for (char *p = buf; *p; p++) if (*p == '#') { while (*p && *p != '\n') *p++ = ' '; if (!*p) break; }
        long *v; int n = parse_ints(buf, &v);
        if (n % 2) { fprintf(stderr, "odd number of integers in config\n"); return 1; }
        struct timespec t0, t1; clock_gettime(CLOCK_MONOTONIC, &t0);
        result_t r; run(v, n / 2, cap, &r);
        clock_gettime(CLOCK_MONOTONIC, &t1);
        if (dumpfn) dump_final(dumpfn);
        print_result(stdout, &r, cap);
        fprintf(stderr, "elapsed %.3f s\n", (t1.tv_sec - t0.tv_sec) + 1e-9 * (t1.tv_nsec - t0.tv_nsec));
        return 0;
    }
    if (!strcmp(mode, "batch")) {
        char *line = NULL; size_t lcap = 0; ssize_t len;
        while ((len = getline(&line, &lcap, stdin)) >= 0) {
            long *v; int n = parse_ints(line, &v);
            if (n % 2) { printf("{\"error\": \"odd number of integers\"}\n"); fflush(stdout); free(v); continue; }
            result_t r; run(v, n / 2, cap, &r);
            reset_grid();
            print_result(stdout, &r, cap);
            free(v);
        }
        return 0;
    }
    fprintf(stderr, "unknown mode %s\n", mode); return 1;
}
