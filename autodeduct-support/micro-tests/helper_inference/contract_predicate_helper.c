/*@ predicate is_enabled(integer value) = value == 1; */

int helper_predicate_flag(int value)
{
    if (value > 0) {
        return 1;
    }
    return 0;
}

/*@
  assigns \nothing;
  ensures value > 0 ==> is_enabled(\result);
  ensures value <= 0 ==> \result == 0;
*/
int entry(int value)
{
    return helper_predicate_flag(value);
}
