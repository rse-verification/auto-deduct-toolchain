/*@ logic integer logic_increment(integer value) = value + 1; */

int helper_logic_increment(int value)
{
    return value + 1;
}

/*@
  requires -1000000 <= value <= 1000000;
  assigns \nothing;
  ensures \result == logic_increment(value);
*/
int entry(int value)
{
    return helper_logic_increment(value);
}
