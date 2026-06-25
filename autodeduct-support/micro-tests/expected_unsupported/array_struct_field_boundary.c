struct sample {
    int value;
    int status;
};

struct sample samples[2];

/*@
  assigns samples[0].value;
  ensures samples[0].value == \old(samples[1].status);
  ensures samples[0].status == \old(samples[0].status);
  ensures samples[1].value == \old(samples[1].value);
  ensures samples[1].status == \old(samples[1].status);
*/
void entry(void)
{
    samples[0].value = samples[1].status;
}
