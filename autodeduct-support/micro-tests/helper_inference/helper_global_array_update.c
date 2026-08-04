int helper_values[4];

void helper_update_slot(int index, int value)
{
    helper_values[index] = value;
}

/*@
  requires 0 <= index < 4;
  assigns helper_values[index];
  ensures helper_values[index] == value;
*/
void entry(int index, int value)
{
    helper_update_slot(index, value);
}
