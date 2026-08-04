int helper_behavior_value(int value)
{
    if (value >= 0) {
        return 10;
    }
    return 20;
}

/*@
  assigns \nothing;

  behavior nonnegative:
    assumes value >= 0;
    ensures \result == 10;

  behavior negative:
    assumes value < 0;
    ensures \result == 20;

  complete behaviors;
  disjoint behaviors;
*/
int entry(int value)
{
    return helper_behavior_value(value);
}
