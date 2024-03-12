// STARTFILE

int sum(int a, int b) {
  return a + b;
}

int mul(int a, int b) {
  return a*b;
}

int mode;
int a;
int b;
int res;

/*@
  requires mode == 0 || mode == 1;
  requires a <= 10 && a >= -10;
  requires b <= 10 && b >= -10;
  assigns res;
  ensures (\old(mode) == 0) ==> (res == \old(a) + \old(b));
  ensures (\old(mode) == 1) ==> (res == \old(a) * \old(b));
*/
void main() {
  int (*funs[2]) (int, int) = {sum, mul};
  res = funs[mode % 2];
}
