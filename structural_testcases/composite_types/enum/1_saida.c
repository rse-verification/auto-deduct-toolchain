// STARTFILE

enum State {
  STATE1,
  STATE2,
  STATE3,
  STATE4,
  ERROR_STATE
};

enum State state;

enum State transition(enum State s) {
  switch (state) {
    case STATE1: return STATE2;
    case STATE2: return STATE3;
    case STATE3: return STATE4;
    case STATE4: return STATE1;
    default: return ERROR_STATE;
  }
}

/*@
  requires state == STATE1 || state == STATE2 || state == STATE3 || state == STATE4;
  assigns state;
  ensures state == STATE1 || state == STATE2 || state == STATE3 || state == STATE4;
*/
void main() {
  state = transition(state);
}