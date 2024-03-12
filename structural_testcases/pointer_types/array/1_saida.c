// STARTFILE

#define SIZE 5
int a[SIZE];
int res;

int sum(int arr[SIZE]) {
    int s = 0;
    for (int i = 0; i < SIZE; ++i) {
      s += arr[i];
    }
    return s;
}

/*@
  requires a[0] <= 10 && a[0] >= -10;
  requires a[1] <= 10 && a[1] >= -10;
  requires a[2] <= 10 && a[2] >= -10;
  requires a[3] <= 10 && a[3] >= -10;
  requires a[4] <= 10 && a[4] >= -10;
  assigns res;
  ensures res == a[0] + a[1] + a[2] + a[3] + a[4];
*/
void main() {
  res = sum(a);
}