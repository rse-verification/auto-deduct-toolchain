struct IntIndexedScalarRecord {
    int level;
    int status;
};

struct IntIndexedScalarRecord int_indexed_scalar_records[2] = {
    {3, 0},
    {8, 1}
};

int helper_read_int_record_level(int index)
{
    return int_indexed_scalar_records[index].level;
}

/*@
  requires 0 <= index < 2;
  assigns \nothing;
  ensures \result == int_indexed_scalar_records[index].level;
*/
int entry(int index)
{
    return helper_read_int_record_level(index);
}
