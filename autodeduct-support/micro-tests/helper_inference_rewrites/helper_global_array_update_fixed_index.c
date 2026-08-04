int helper_rewrite_values[4];

void helper_update_first_slot(void)
{
    helper_rewrite_values[0] = 1;
}

/*@
  assigns helper_rewrite_values[0];
  ensures helper_rewrite_values[0] == 1;
*/
void entry(void)
{
    helper_update_first_slot();
}
