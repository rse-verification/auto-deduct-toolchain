enum RecordSlot {
    RECORD_LOW = 0,
    RECORD_HIGH = 1
};

struct SlotRecord {
    int level;
    int status;
};

struct SlotRecord records[2] = {
    {3, 0},
    {8, 1}
};

struct SlotRecord helper_read_record(enum RecordSlot slot)
{
    return records[slot];
}

/*@
  assigns \nothing;
  ensures \result == 8;
*/
int entry(void)
{
    struct SlotRecord selected = helper_read_record(RECORD_HIGH);
    return selected.level;
}
