void helper_store_value(int *target, int value)
{
    *target = value;
}

/*@
  requires \valid(target);
  assigns *target;
  ensures *target == value;
*/
void entry(int *target, int value)
{
    helper_store_value(target, value);
}
