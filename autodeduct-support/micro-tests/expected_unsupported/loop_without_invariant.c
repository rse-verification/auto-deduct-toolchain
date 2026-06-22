/*@
  requires 0 <= count <= 100;
  assigns \nothing;
  ensures \result >= 0;
*/
int entry(int count)
{
    int total = 0;
    int index = 0;
    while (index < count) {
        total = total + index;
        index = index + 1;
    }
    return total;
}
