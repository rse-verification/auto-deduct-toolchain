void helper_store_stack_value(int *target, int value)
{
    *target = value;
}

/*@
  assigns \nothing;
  ensures \result == value;
*/
int entry(int value)
{
    int local = 0;
    helper_store_stack_value(&local, value);
    return local;
}
