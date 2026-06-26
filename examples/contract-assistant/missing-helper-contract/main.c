#include <limits.h>

#include "account.h"

int input;
int result;

/*@
  requires INT_MIN < input < INT_MAX;
  assigns result;
  ensures result == input + 1;
*/
int main(void) {
  Account account = { input };

  deposit_one(&account);

  result = account.balance;

  return 0;
}
