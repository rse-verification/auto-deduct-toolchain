struct SingleGlobalRecord {
    int level;
    int status;
};

struct SingleGlobalRecord single_global_record = {
    3,
    0
};

int helper_read_single_global_level(void)
{
    return single_global_record.level;
}

/*@
  assigns \nothing;
  ensures \result == single_global_record.level;
*/
int entry(void)
{
    return helper_read_single_global_level();
}
