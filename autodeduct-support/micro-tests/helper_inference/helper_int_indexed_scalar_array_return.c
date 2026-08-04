int scalar_array_values[2] = {
    3,
    8
};

int helper_read_scalar_array_value(int index)
{
    return scalar_array_values[index];
}

/*@
  requires 0 <= index < 2;
  assigns \nothing;
  ensures \result == scalar_array_values[index];
*/
int entry(int index)
{
    return helper_read_scalar_array_value(index);
}
