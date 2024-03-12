// STARTFILE

float a;
float b;

float pow2(float x) {
    return x*x;
}

/*@
  requires a <= 1000. && a >= -1000.f;
  assigns b;
  ensures b == \old(a)*\old(a);
*/
void main() {
  b = pow2(a);
}