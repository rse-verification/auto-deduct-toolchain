enum RecordSlotRewrite {
    RECORD_REWRITE_LOW = 0,
    RECORD_REWRITE_HIGH = 1
};

struct SlotRecordRewrite {
    int level;
    int status;
};

struct SlotRecordRewrite rewrite_records[2] = {
    {3, 0},
    {8, 1}
};

int helper_read_record_level(enum RecordSlotRewrite slot)
{
    return rewrite_records[slot].level;
}

/*@
  assigns \nothing;
  ensures \result == 8;
*/
int entry(void)
{
    return helper_read_record_level(RECORD_REWRITE_HIGH);
}
