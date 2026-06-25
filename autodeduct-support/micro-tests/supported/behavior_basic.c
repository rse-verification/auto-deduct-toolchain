int output;

/*@
  assigns output;

  behavior nonnegative:
    assumes value >= 0;
    ensures output == 1;

  behavior negative:
    assumes value < 0;
    ensures output == 0;

  complete behaviors;
  disjoint behaviors;
*/
void entry(int value)
{
    if (value >= 0) {
        output = 1;
    } else {
        output = 0;
    }
}
