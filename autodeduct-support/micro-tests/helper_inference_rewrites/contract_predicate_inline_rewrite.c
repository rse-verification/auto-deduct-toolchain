int helper_inline_predicate_flag(int value)
{
    if (value > 0) {
        return 1;
    }
    return 0;
}

/*@
  assigns \nothing;
  ensures value > 0 ==> \result == 1;
  ensures value <= 0 ==> \result == 0;
*/
int entry(int value)
{
    return helper_inline_predicate_flag(value);
}
