typedef unsigned char byte;

#define TRUE_VALUE 1
#define FALSE_VALUE 0
#define GOOD_STATUS(status) (((status) >= 10) ? TRUE_VALUE : FALSE_VALUE)

typedef struct {
    byte value;
    byte status;
} SmallSignal;

typedef enum {
    SIGNAL_CURRENT,
    SIGNAL_PREVIOUS,
    SIGNAL_COUNT
} SignalId;

SmallSignal signals[SIGNAL_COUNT];
byte remembered;

void remember_previous(void)
{
    remembered = TRUE_VALUE;
}

/*@ logic byte rememberedAlias = remembered; */
/*@ logic SmallSignal previousSignal = signals[SIGNAL_PREVIOUS]; */

/*@
    assigns remembered;

    ensures (\old(rememberedAlias) == FALSE_VALUE
        && GOOD_STATUS(\old(previousSignal.status)) == TRUE_VALUE)
        ==> rememberedAlias == TRUE_VALUE;
*/
void entry(void)
{
    remember_previous();
}
