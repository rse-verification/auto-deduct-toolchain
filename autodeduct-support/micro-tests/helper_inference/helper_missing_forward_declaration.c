int state;

/*@
    assigns state;
    ensures state == 1;
*/
void entry(void)
{
    helper_late();
}

void helper_late(void)
{
    state = 1;
}
