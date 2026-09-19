/* Independent C Langton's Ant per CONVENTIONS.md: hash-free flat grid, prints onset & mismatch count.
   usage: ./myant N   */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char**argv){
  long N=atol(argv[1]); int P=104;
  int G=2*(int)(2*N/104)+600, OFF=G/2;
  unsigned char*g=calloc((size_t)G*G,1); char*t=malloc(N+2);
  static const int DX[4]={0,1,0,-1}, DY[4]={1,0,-1,0}; /* N E S W; right = +1 */
  int x=0,y=0,d=0; long minx=0,maxx=0,miny=0,maxy=0;
  for(long k=1;k<=N;k++){
    if(x<=-OFF+1||x>=OFF-1||y<=-OFF+1||y>=OFF-1){fprintf(stderr,"bounds\n");return 2;}
    unsigned char*c=&g[(size_t)(x+OFF)*G+(y+OFF)];
    if(*c){d=(d+3)&3;t[k]='L';}else{d=(d+1)&3;t[k]='R';}
    *c^=1; x+=DX[d]; y+=DY[d];
  }
  long s=0; for(long k=N-P;k>=1;k--) if(t[k]!=t[k+P]){s=k;break;}
  long mism=0; for(long k=s+1;k+P<=N;k++) if(t[k]!=t[k+P]) mism++;
  printf("N=%ld s=%ld t[s]=%c t[s+104]=%c mismatches_after_s=%ld periods=%ld final=(%d,%d) dir=%d\n",N,s,t[s],t[s+P],mism,(N-P-s)/P,x,y,d);
  return 0;
}
