int helper_return_value(int value)
{
    return value;
}

/*@
  assigns \nothing;
  ensures \result == value;
*/
int entry(int value)
{
    return helper_return_value(value);
}
