struct record {
    int value;
    int flag;
};

struct record current;

/*@
  assigns current.value, current.flag;
  ensures current.value == 1;
  ensures current.flag == 1;
*/
void entry(void)
{
    /*@ assert \valid(&current); */
    (&current)->value = 1;
    (&current)->flag = 1;
}
