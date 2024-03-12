// STARTFILE

char c;

char update_state(char a) {
  if (a != 'z') {
    return a+1;
  } else {
    return 'z';
  }
}

/*@
  requires c == 'a' || c == 'b' || c == 'c';
  assigns c;
  ensures c == 'b' || c == 'c' || c == 'd';
*/
void main() {
  c = update_state(c);
}