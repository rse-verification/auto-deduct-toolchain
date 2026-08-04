int helper_inline_increment(int value)
{
    return value + 1;
}

/*@
  requires -1000000 <= value <= 1000000;
  assigns \nothing;
  ensures \result == value + 1;
*/
int entry(int value)
{
    return helper_inline_increment(value);
}
