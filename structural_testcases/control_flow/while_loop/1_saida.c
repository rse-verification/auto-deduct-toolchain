// STARTFILE

#include <limits.h>

int a;
int b;
int s;

int sum(int a, int b) {
  int s = 0;
  while (a <= b) {
    s = a;
    a++;
  }
  return s;
}

/*@
  requires a >= 0 && a <= 1000;
  requires b >= 0 && b <= 1000;
  requires a <= b;
  assigns s;
  ensures s == \sum(a, b, \lambda integer k; k);
*/
void main() {
  s = sum(a, b);
}