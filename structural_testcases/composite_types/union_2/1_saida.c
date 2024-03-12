// STARTFILE

union Addr {
    unsigned char bytes[4];
    unsigned int full_addr;
};

union Addr addr;
int index;
int b;

void write_addr(unsigned char bte, int idx) {
  switch (idx) {
    case 0: 
      addr.bytes[0] = bte;
      break;
    case 1: 
      addr.bytes[1] = bte;
      break;
    case 2: 
      addr.bytes[2] = bte;
      break;
    case 3: 
      addr.bytes[3] = bte;
      break;
    default: 
      break; 
  }
}

/*@
  requires index >= 0 && index < 4;
  requires addr.full_addr == 0x0;
  requires b == 0xAA;
  ensures (addr.bytes[0] == 0xAA && addr.full_addr == 0xAA) 
    ||    (addr.bytes[1] == 0xAA && addr.full_addr == 0x00AA) 
    ||    (addr.bytes[2] == 0xAA && addr.full_addr == 0x0000AA) 
    ||    (addr.bytes[3] == 0xAA && addr.full_addr == 0x000000AA);
*/
void main() {
  write_addr(b, index);
}