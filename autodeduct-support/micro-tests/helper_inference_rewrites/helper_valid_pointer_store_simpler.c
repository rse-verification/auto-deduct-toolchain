int helper_store_through_local_pointer(void)
{
    int local = 0;
    int *target = &local;
    *target = 1;
    return local;
}

/*@
  assigns \nothing;
  ensures \result == 1;
*/
int entry(void)
{
    return helper_store_through_local_pointer();
}
