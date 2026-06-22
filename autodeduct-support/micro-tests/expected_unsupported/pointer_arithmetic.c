/*@
  requires \valid(base + (0 .. 1));
  assigns base[0];
  ensures base[0] == \old(base[1]);
*/
void entry(int *base)
{
    *base = *(base + 1);
}
