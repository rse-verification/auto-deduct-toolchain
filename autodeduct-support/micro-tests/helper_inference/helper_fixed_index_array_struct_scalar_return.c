struct FixedIndexRecord {
    int level;
    int status;
};

struct FixedIndexRecord fixed_index_records[2] = {
    {3, 0},
    {8, 1}
};

int helper_read_fixed_record_level(void)
{
    return fixed_index_records[0].level;
}

/*@
  assigns \nothing;
  ensures \result == fixed_index_records[0].level;
*/
int entry(void)
{
    return helper_read_fixed_record_level();
}
