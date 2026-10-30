#include "presonus/application/LPCProgrammerGeometry.hpp"
#include <cassert>
#include <cstdarg>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <termios.h>
#include <unistd.h>
static int fd, g, f, res, kind, byte, count, debugs;
static termios captured;
static int stage;
extern "C" int __wrap_open(const char *path, int flags, ...) {
  assert(std::strcmp(path, "/offline/serial") == 0);
  assert(flags == (O_RDWR | O_NOCTTY | O_NONBLOCK));
  assert(stage++ == 0);
  return fd;
}
extern "C" int __wrap_tcgetattr(int x, termios *t) {
  assert(x == fd && stage++ == 1);
  std::memset(t, 0x5a, sizeof(*t));
  return g;
}
extern "C" void __real_cfmakeraw(termios *);
extern "C" void __wrap_cfmakeraw(termios *t) {
  assert(stage++ == 2);
  assert(t->c_iflag == (IGNPAR | IGNBRK | IXON | IXOFF));
  assert(t->c_cflag == (B115200 | CS8 | CLOCAL | CREAD));
  __real_cfmakeraw(t);
}
extern "C" int __wrap_tcflush(int x, int q) {
  assert(x == fd && q == TCIFLUSH && stage++ == 3);
  return f;
}
extern "C" int __wrap_tcsetattr(int x, int q, const termios *t) {
  assert(x == fd && q == TCSANOW && stage++ == 4);
  captured = *t;
  return res;
}
extern "C" ssize_t __wrap_write(int x, const void *p, size_t n) {
  assert(x == fd && n == 1 && *(const unsigned char *)p == byte);
  ++count;
  return res;
}
extern "C" int __wrap_close(int x) {
  assert(x == fd);
  ++count;
  return res;
}
extern "C" void captureDebug(const char *,
                             ...) asm("__wrap__ZN4Core11DebugPrintfEPKcz");
extern "C" void captureDebug(const char *, ...) { ++debugs; }
int main() {
  int expectedfd;
  unsigned expected;
  size_t total = 0;
  while (std::cin >> kind >> fd >> g >> f >> res >> byte >> expected >>
         expectedfd) {
    stage = count = debugs = 0;
    presonus::lpc::InputState initial;
    initial.descriptor = fd;
    Presonus::LPCProgrammer p(presonus::lpc::InputOnly{}, initial);
    int result = kind == 0   ? p.openPort("/offline/serial")
                 : kind == 1 ? p.writeChar(static_cast<unsigned char>(byte))
                             : p.close();
    assert(static_cast<unsigned>(result) == expected);
    assert(presonus::lpc::InputAccess::state(p).descriptor == expectedfd);
    if (kind == 0) {
      assert(stage == (fd < 0 ? 1 : 5));
      assert(debugs == (fd < 0 || res != 0));
      if (fd >= 0) {
        assert(captured.c_iflag == 4100 && captured.c_oflag == 0 &&
               captured.c_lflag == 0 && captured.c_cflag == 6322);
        assert(captured.c_cc[VTIME] == 1 && captured.c_cc[VMIN] == 0);
      }
    } else
      assert(count == 1);
    ++total;
  }
  std::cout << "PASS transport_cases=" << total << "\n";
}
