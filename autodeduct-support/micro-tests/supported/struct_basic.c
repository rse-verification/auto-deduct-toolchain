struct cell {
    int value;
    int flag;
};

struct cell current;

/*@
  assigns current.value, current.flag;
  ensures current.value == value;
  ensures current.flag == (value >= 0 ? 1 : 0);
*/
void entry(int value)
{
    current.value = value;
    if (value >= 0) {
        current.flag = 1;
    } else {
        current.flag = 0;
    }
}
