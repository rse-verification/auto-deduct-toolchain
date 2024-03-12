// STARTFILE

union Addr {
    struct {
        unsigned char b1;
        unsigned char b2;
        unsigned char b3;
        unsigned char b4;
    } bytes;
    unsigned int full_addr;
};

union Addr addr;
int index;
int b;

void write_addr(unsigned char bte, int idx) {
  switch (idx) {
    case 0: 
      addr.bytes.b1 = bte;
      break;
    case 1: 
      addr.bytes.b2 = bte;
      break;
    case 2: 
      addr.bytes.b3 = bte;
      break;
    case 3: 
      addr.bytes.b4 = bte;
      break;
    default: 
      break; 
  }
}

/*@
  requires index >= 0 && index < 4;
  requires addr.full_addr == 0x0;
  requires b == 0xAA;
  ensures (addr.bytes.b1 == 0xAA && addr.full_addr == 0xAA) 
    ||    (addr.bytes.b2 == 0xAA && addr.full_addr == 0xAA00) 
    ||    (addr.bytes.b3 == 0xAA && addr.full_addr == 0xAA0000) 
    ||    (addr.bytes.b4 == 0xAA && addr.full_addr == 0xAA000000);
*/
void main() {
  write_addr(b, index);
}