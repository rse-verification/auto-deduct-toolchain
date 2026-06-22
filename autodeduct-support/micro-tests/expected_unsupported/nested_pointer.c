/*@
  requires \valid(target);
  requires \valid(*target);
  assigns **target;
  ensures **target == value;
*/
void entry(int **target, int value)
{
    **target = value;
}
