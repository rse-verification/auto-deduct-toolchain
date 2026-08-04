struct IntIndexedRecord {
    int level;
    int status;
};

struct IntIndexedRecord int_indexed_records[2] = {
    {3, 0},
    {8, 1}
};

struct IntIndexedRecord helper_read_int_record(int index)
{
    return int_indexed_records[index];
}

/*@
  requires 0 <= index < 2;
  assigns \nothing;
  ensures \result == int_indexed_records[index].level;
*/
int entry(int index)
{
    struct IntIndexedRecord selected = helper_read_int_record(index);
    return selected.level;
}
