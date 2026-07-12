typedef unsigned char BoolValue;
typedef unsigned char StatusValue;

#define ACTIVE_VALUE ((BoolValue)1)
#define READY_STATUS ((StatusValue)10)

typedef struct {
    BoolValue value;
    StatusValue status;
} BoolSignal;

typedef enum {
    INPUT_ID,
    PREVIOUS_ID,
    SIGNAL_COUNT
} SignalId;

BoolSignal signals[SIGNAL_COUNT];
BoolSignal output;

/*@
  requires 0 <= signal && signal < SIGNAL_COUNT;
  assigns \nothing;
  ensures \valid_read(&signals[signal]);
  ensures \result == signals[signal];
*/
BoolSignal read_signal(SignalId signal)
{
    return signals[signal];
}

/*@
  assigns output.value;
  ensures output.value == \old(signals[INPUT_ID].value) ||
          output.value == 0;
*/
void entry(void)
{
    BoolSignal input = read_signal(INPUT_ID);

    if (input.value == ACTIVE_VALUE && input.status >= READY_STATUS) {
        output.value = input.value;
    } else {
        output.value = 0;
    }
}
