// STARTFILE

union U {
  long long lval;
  int ival1;
  int ival2;
};

union U u;

int a;
int b;
long long c;
int res;
long long res2;

int add(int a, int b) {
    return a + b;
}

long long ladd(long long a, long long b) {
    return a + b;
}

/*@
  requires a <= 100 && a >= -100;
  requires b <= 100 && b >= -100;
  requires c <= 100 && c >= -100;
  assigns res;
  assigns res2;
  ensures res == (a + b);
  ensures res2 == (c + c);
*/
void main() {
  u.lval = c;
  res2 = ladd(c, c);
  u.ival1 = a;
  u.ival2 = b;
  res = add(a, b);
}