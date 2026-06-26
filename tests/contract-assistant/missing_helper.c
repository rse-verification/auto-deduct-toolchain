#include <limits.h>

int input;
int result;

void maybe_add(int *p, int flag) {
  if (flag) {
    *p = *p + 1;
  }
}

/*@
  requires INT_MIN <= input < INT_MAX;
  ensures result >= input;
*/
int main(void) {
  int x = input;
  maybe_add(&x, input);
  result = x;
  return 0;
}
