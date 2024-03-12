// STARTFILE

#define SIZE 5
int d1;
int d2;
int d3;
int d4;
int d5;

int res;

int sum(int* arr) {
    int s = 0;
    for (int i = 0; i < SIZE; ++i) {
      s += arr[i];
    }
    return s;
}

/*@
  requires d1 <= 10 && d1 >= -10;
  requires d2 <= 10 && d2 >= -10;
  requires d3 <= 10 && d3 >= -10;
  requires d4 <= 10 && d4 >= -10;
  requires d4 <= 10 && d5 >= -10;
  assigns res;
  ensures res == d1 + d2 + d3 + d4 + d5;
*/
void main() {
  int a[5];
  a[0] = d1;
  a[1] = d2;
  a[2] = d3;
  a[3] = d4;
  a[4] = d5;
  res = sum(a);
}