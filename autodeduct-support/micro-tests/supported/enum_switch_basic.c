enum choice {
    CHOICE_ZERO = 0,
    CHOICE_ONE = 1,
    CHOICE_OTHER = 2
};

int selected;

/*@
  assigns selected;
  ensures mode == CHOICE_ZERO ==> selected == 0;
  ensures mode == CHOICE_ONE ==> selected == 1;
  ensures mode != CHOICE_ZERO && mode != CHOICE_ONE ==> selected == 2;
*/
void entry(enum choice mode)
{
    switch (mode) {
    case CHOICE_ZERO:
        selected = 0;
        break;
    case CHOICE_ONE:
        selected = 1;
        break;
    default:
        selected = 2;
        break;
    }
}
