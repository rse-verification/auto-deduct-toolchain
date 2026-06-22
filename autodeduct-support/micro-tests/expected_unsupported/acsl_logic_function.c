/*@ logic integer twice(integer value) = value + value; */

/*@
  requires -1000 <= value <= 1000;
  assigns \nothing;
  ensures \result == twice(value);
*/
int entry(int value)
{
    return value + value;
}
