typedef unsigned char tB;
typedef unsigned char tU08;

#define TRUE_VALUE ((tB)1)
#define GOOD_STATUS ((tU08)10)

typedef struct {
    tB val_B;
    tU08 ss_U08;
} tBS;

typedef enum {
    INPUT_SIGNAL,
    PREVIOUS_SIGNAL,
    NUM_B_SIG_E
} SIGNAL_B;

tBS signal_store[NUM_B_SIG_E];
tBS output_signal;

/*@
  requires 0 <= signal && signal < NUM_B_SIG_E;
  assigns \nothing;
  ensures \valid_read(&signal_store[signal]);
  ensures \result == signal_store[signal];
*/
tBS read_signal(SIGNAL_B signal)
{
    return signal_store[signal];
}

/*@
  assigns output_signal.val_B;
  ensures output_signal.val_B == \old(signal_store[INPUT_SIGNAL].val_B) ||
          output_signal.val_B == 0;
*/
void entry(void)
{
    tBS input = read_signal(INPUT_SIGNAL);

    if (input.val_B == TRUE_VALUE && input.ss_U08 >= GOOD_STATUS) {
        output_signal.val_B = input.val_B;
    } else {
        output_signal.val_B = 0;
    }
}
