int counter;

/*@
  requires counter < 2147483647;
  assigns counter;
  ensures counter == \old(counter) + 1;
*/
void entry(void)
{
    counter = counter + 1;
}
