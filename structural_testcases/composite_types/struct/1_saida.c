// STARTFILE

struct Vector {
  int a;
  int b;
};

struct Vector v1;
struct Vector v2;
int res;

int pow2(struct Vector x1, struct Vector x2) {
    return x1.a*x1.b+x2.a*x2.b;
}

/*@
  requires v1.a <= 100 && v1.a >= -100;
  requires v1.b <= 100 && v1.b >= -100;
  requires v2.a <= 100 && v2.a >= -100;
  requires v2.b <= 100 && v2.b >= -100;
  assigns res;
  ensures res == \old(v1.a)*\old(v1.b) + \old(v2.a)*\old(v2.b);
*/
void main() {
  res = pow2(v1,v2);
}