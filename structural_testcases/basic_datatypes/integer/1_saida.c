// STARTFILE

int a;
int b;

int pow2(int x) {
    return x*x;
}

/*@
  requires a <= 1000 && a >= -1000;
  assigns b;
  ensures b == \old(a)*\old(a);
*/
void main() {
  b = pow2(a);
}