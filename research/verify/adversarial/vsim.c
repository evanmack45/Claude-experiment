/* vsim.c -- independent Langton's-ant verifier written from research/CONVENTIONS.md
 * for research/verify/adversarial.  Deliberately different design from antsim.c:
 * the full turn sequence t[1..n] and position sequence pos[0..n] are stored and the
 * onset / certification are computed POST HOC by full rescans at checkpoints.
 *
 *   ./vsim run <cfgfile> [--cap N] [--grid G]
 *   ./vsim batch [--cap N] [--grid G]        (one config per stdin line; ints are x y pairs)
 *
 * Conventions: ant at (0,0) facing N=(0,+1); white -> right turn (N->E->S->W), black -> left;
 * flip; move.  t[k] = 1 if step k turned right.  Onset s = smallest s>=0 with t[k]==t[k+104]
 * for all k>=s+1 (== max{k: t[k]!=t[k+104]}).  Certification: n-104-s >= 2080 (20 periods
 * verified) and pos[n] >= 20 cells beyond the bbox of {origin, initial black cells, cells
 * read in steps 1..s} in both coordinates in the travel direction sign(pos[n]-pos[n-104]).
 * cert_step = first such n.  contact = first step whose read cell was initially black.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <ctype.h>
#define P 104
#define NPER 20
#define MARG 20
static long G = 8192, O;
static unsigned char *grid;      /* bit0 colour, bit1 initially black */
static long *tlist; static long ntl, tlcap;
static unsigned char *t; static int *px, *py; static long cap;
static void touch(long i){ if(ntl==tlcap){tlcap*=2; tlist=realloc(tlist,tlcap*sizeof(long));} tlist[ntl++]=i; }
static int nparse(const char *s, long **out){ int n=0,c=256; long *v=malloc(c*sizeof(long)); const char *p=s;
  while(*p){ if(isdigit((unsigned char)*p)||((*p=='-'||*p=='+')&&isdigit((unsigned char)p[1]))){char *e; long x=strtol(p,&e,10); if(n==c){c*=2;v=realloc(v,c*sizeof(long));} v[n++]=x; p=e;} else p++; }
  *out=v; return n; }
static void simulate(const long *cfg, int nc){
  ntl=0; long ix0=O,ix1=O,iy0=O,iy1=O; int nb=0; long contact=0;
  for(int i=0;i<nc;i++){ long x=O+cfg[2*i], y=O+cfg[2*i+1];
    if(x<1||x>=G-1||y<1||y>=G-1){printf("{\"outcome\":\"error\",\"msg\":\"cell outside grid\"}\n");return;}
    long id=y*G+x; if(grid[id]&1) continue; grid[id]=3; touch(id); nb++;
    if(x<ix0)ix0=x;
    if(x>ix1)ix1=x;
    if(y<iy0)iy0=y;
    if(y>iy1)iy1=y; }
  long x=O,y=O; int d=0; /* 0=N 1=E 2=S 3=W */
  static const int dx[4]={0,1,0,-1}, dy[4]={1,0,-1,0};
  px[0]=(int)x; py[0]=(int)y; long n=0; const char *outcome="notcert"; long s=-1, cert=-1; int dispx=0,dispy=0; int nblack=nb;
  int boundary=0;
  while(n<cap){
    n++; long id=y*G+x; unsigned char c=grid[id];
    if(c&1){ d=(d+3)&3; t[n]=0; nblack--; if(!contact && (c&2)) contact=n; }
    else   { d=(d+1)&3; t[n]=1; nblack++; }
    if(!(c&2) && !(c&4)){ touch(id); }  /* bit2 marks "ever touched" for reset */
    grid[id]=(unsigned char)((c&2)|4|((c&1)^1));
    x+=dx[d]; y+=dy[d]; px[n]=(int)x; py[n]=(int)y;
    if(x<=0||x>=G-1||y<=0||y>=G-1){ boundary=1; break; }
    if((n & 2047)==0 || n==cap){
      /* full rescan for the last mismatch */
      long L=0; for(long k=1;k+P<=n;k++) if(t[k]!=t[k+P]) L=k;
      if(n-P-L >= NPER*P){
        long bx0=ix0,bx1=ix1,by0=iy0,by1=iy1; /* origin included via px[0] */
        long kmax = L-1; if(kmax<0) kmax=0;   /* pos[0..s-1] = cells read in steps 1..s; pos[0] = origin always */
        for(long k=0;k<=kmax;k++){ if(px[k]<bx0)bx0=px[k]; if(px[k]>bx1)bx1=px[k]; if(py[k]<by0)by0=py[k]; if(py[k]>by1)by1=py[k]; }
        for(long m=L+P+NPER*P; m<=n; m++){
          int ddx=px[m]-px[m-P], ddy=py[m]-py[m-P];
          if(ddx==0||ddy==0) continue;
          int okx = ddx>0 ? (px[m]>=bx1+MARG) : (px[m]<=bx0-MARG);
          int oky = ddy>0 ? (py[m]>=by1+MARG) : (py[m]<=by0-MARG);
          if(okx&&oky){ cert=m; s=L; dispx=ddx; dispy=ddy; outcome="certified"; break; }
        }
        if(cert>=0){ /* sanity: no mismatch after L up to cert */
          for(long k=L+1;k+P<=cert;k++) if(t[k]!=t[k+P]){ outcome="INTERNAL_ERROR"; }
          break; }
      }
    }
  }
  if(boundary) outcome="boundary";
  if(s<0){ long L=0; for(long k=1;k+P<=n;k++) if(t[k]!=t[k+P]) L=k; s=L; }
  const char *dir="none"; if(cert>=0) dir = dispx>0 ? (dispy>0?"+x,+y":"+x,-y") : (dispy>0?"-x,+y":"-x,-y");
  printf("{\"outcome\":\"%s\",\"onset\":%ld,\"direction\":\"%s\",\"disp\":[%d,%d],\"cert_step\":%ld,\"contact\":%ld,\"n_black_init\":%d,\"steps\":%ld,\"final_pos\":[%ld,%ld]}\n",
    outcome,s,dir,dispx,dispy,cert,contact,nb,n,x-O,y-O);
  fflush(stdout);
  for(long i=0;i<ntl;i++) grid[tlist[i]]=0;
  ntl=0;
}
int main(int argc,char**argv){
  if(argc<2){fprintf(stderr,"usage\n");return 1;}
  cap=1L<<23; const char *cfgf=NULL;
  for(int i=2;i<argc;i++){ if(!strcmp(argv[i],"--cap")) cap=atol(argv[++i]); else if(!strcmp(argv[i],"--grid")) G=atol(argv[++i]); else cfgf=argv[i]; }
  O=G/2; grid=calloc((size_t)G*G,1); tlcap=1<<16; tlist=malloc(tlcap*sizeof(long));
  t=malloc(cap+2); px=malloc((cap+2)*sizeof(int)); py=malloc((cap+2)*sizeof(int));
  if(!grid||!t||!px||!py){fprintf(stderr,"alloc\n");return 1;}
  if(!strcmp(argv[1],"run")){ FILE*f=fopen(cfgf,"r"); if(!f){fprintf(stderr,"open\n");return 1;}
    fseek(f,0,SEEK_END); long sz=ftell(f); fseek(f,0,SEEK_SET); char*b=malloc(sz+1); size_t rd=fread(b,1,sz,f); b[rd]=0; fclose(f);
    for(char*p=b;*p;p++) if(*p=='#'){ while(*p&&*p!='\n') *p++=' '; if(!*p)break; }
    long*v; int n=nparse(b,&v); if(n%2){fprintf(stderr,"odd\n");return 1;} simulate(v,n/2); return 0; }
  if(!strcmp(argv[1],"batch")){ char*line=NULL; size_t lc=0; while(getline(&line,&lc,stdin)>=0){ long*v; int n=nparse(line,&v); if(n%2){printf("{\"outcome\":\"error\"}\n");continue;} simulate(v,n/2); free(v);} return 0; }
  return 1;
}
