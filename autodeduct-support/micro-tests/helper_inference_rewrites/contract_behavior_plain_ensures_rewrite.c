int helper_plain_behavior_value(int value)
{
    if (value >= 0) {
        return 10;
    }
    return 20;
}

/*@
  assigns \nothing;
  ensures value >= 0 ==> \result == 10;
  ensures value < 0 ==> \result == 20;
*/
int entry(int value)
{
    return helper_plain_behavior_value(value);
}
