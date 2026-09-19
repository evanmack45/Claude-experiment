/* Tests on a shrunken grid: (1) a run that hits the grid edge is reported as 'boundary' with the ant on the outer ring,
   never wrapped; (2) after such a run (and after any run) the grid is fully reset: the empty grid run next gives 9977/12336;
   (3) running the same configuration twice gives identical results (no stale cells); (4) overall cell array is all-zero after runs. */
#include "randexp_lib.c"
static int check(const char *what, int cond) { printf("%-70s %s\n", what, cond ? "OK" : "FAIL"); return !cond; }
int main(void) {
    cells = calloc((size_t)GRID * GRID, 1);
    touched = malloc(sizeof(int32_t) * ((size_t)GRID * GRID + 16));
    int fails = 0;
    uint8_t *cfg = malloc(64 * 64);
    result_t a, b, e;
    /* k=64 p=0.5 sample 0: pre-onset bbox typically > +-27, so on GRID=96 (origin 48) the 20-cell escape needs |coord|>=47 -> boundary */
    gen_config(64, 0.5, 20260919, 0, cfg);
    run(64, cfg, 20000000, &a);
    printf("GRID=%d k=64 sample0: status=%s steps=%lld s=%lld final=(%d,%d) bbox=(%d,%d,%d,%d)\n", GRID, STNAME[a.status], (long long)a.steps, (long long)a.s, a.fx, a.fy, a.bx0, a.by0, a.bx1, a.by1);
    fails += check("boundary run reported as ST_BOUNDARY", a.status == ST_BOUNDARY);
    fails += check("ant is on the outer ring (x or y == 0 or GRID-1), not wrapped", (a.fx + ORIGIN <= 0 || a.fx + ORIGIN >= GRID - 1 || a.fy + ORIGIN <= 0 || a.fy + ORIGIN >= GRID - 1));
    long nz = 0; for (size_t i = 0; i < (size_t)GRID * GRID; i++) nz += cells[i] != 0;
    fails += check("cells array all zero after boundary run", nz == 0);
    uint8_t empty[1] = {0};
    run(1, empty, 20000000, &e);
    printf("empty grid after boundary run: status=%s s=%lld steps=%lld dir=%s final=(%d,%d)\n", STNAME[e.status], (long long)e.s, (long long)e.steps, DIRNAME[e.dirid], e.fx, e.fy);
    fails += check("empty grid gives certified s=9977 cert=12336 -x,-y", e.status == ST_CERT && e.s == 9977 && e.steps == 12336 && e.dirid == 3);
    /* same config twice */
    gen_config(5, 0.5, 20260919, 3, cfg); run(5, cfg, 20000000, &a);
    gen_config(64, 0.5, 20260919, 1, cfg); run(64, cfg, 20000000, &b);  /* something big in between */
    gen_config(5, 0.5, 20260919, 3, cfg); run(5, cfg, 20000000, &b);
    fails += check("same config run twice (with another run in between) gives identical result", a.status == b.status && a.s == b.s && a.steps == b.steps && a.fx == b.fx && a.fy == b.fy && a.bx0 == b.bx0 && a.bx1 == b.bx1 && a.by0 == b.by0 && a.by1 == b.by1);
    nz = 0; for (size_t i = 0; i < (size_t)GRID * GRID; i++) nz += cells[i] != 0;
    fails += check("cells array all zero at end", nz == 0);
    printf("%d failures\n", fails);
    return fails != 0;
}
