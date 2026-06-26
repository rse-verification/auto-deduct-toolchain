#include "account.h"

void deposit_one(Account *account) {
  account->balance = account->balance + 1;
}
