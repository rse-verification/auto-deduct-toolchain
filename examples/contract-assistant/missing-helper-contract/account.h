#ifndef ACCOUNT_H
#define ACCOUNT_H

typedef struct {
  int balance;
} Account;

void deposit_one(Account *account);

#endif
