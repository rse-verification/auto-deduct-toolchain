int values[2];

/*@
  assigns values[0];
  ensures values[0] == value;
  ensures values[1] == \old(values[1]);
*/
void entry(int value)
{
    values[0] = value;
}
