#include "presonus/uc/firmware_update_listener.hpp"
#include <array>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <iostream>
#include <sstream>
#include <string>
#include <termios.h>
#include <unistd.h>
#include <vector>
#define private public
#include "presonus/application/LPCProgrammerGeometry.hpp"
#undef private
#include "../current_static104/LocalSymbolRuntime104.hpp"
namespace {
std::vector<std::string> events;
std::vector<std::string> responses;
std::string pending, writing;
unsigned responseIndex{};
bool portSuccess = true, emptyClock = false, capture = false;
unsigned clockMilliseconds = 1250;
void *deleting{};
std::string hex(const unsigned char *p, std::size_t n) {
  static const char digits[] = "0123456789abcdef";
  std::string s;
  for (std::size_t i = 0; i < n; ++i) {
    s += digits[p[i] >> 4];
    s += digits[p[i] & 15];
  }
  return s;
}
std::string hex(const std::string &s) {
  return hex(reinterpret_cast<const unsigned char *>(s.data()), s.size());
}
void event(std::string s) {
  if (capture)
    events.push_back(s);
}
struct Listener : Presonus::UC::IFirmwareUpdateListener {
  void onProgress(const char *text, float value) override {
    std::uint32_t bits;
    std::memcpy(&bits, &value, 4);
    event("progress " + hex(std::string(text)) + " " + std::to_string(bits));
  }
};
} // namespace
extern "C" int __wrap_printf(const char *format, ...) {
  char text[4096];
  va_list args;
  va_start(args, format);
  int n = std::vsnprintf(text, sizeof(text), format, args);
  va_end(args);
  // openPort is an explicit native provider boundary, whose own diagnostics
  // are outside this new-method oracle domain.
  if (std::strncmp(text, "Can't open COM-Port", 19) != 0)
    event("debug " + hex(std::string(text)));
  return n;
}
extern "C" int __wrap___printf_chk(int, const char *format, ...) {
  char text[4096];
  va_list args;
  va_start(args, format);
  int n = std::vsnprintf(text, sizeof(text), format, args);
  va_end(args);
  // openPort is an explicit native provider boundary, whose own diagnostics
  // are outside this new-method oracle domain.
  if (std::strncmp(text, "Can't open COM-Port", 19) != 0)
    event("debug " + hex(std::string(text)));
  return n;
}
extern "C" int __wrap_fflush(FILE *) { return 0; }
extern "C" ssize_t __wrap_write(int fd, const void *data, std::size_t n) {
  if (fd != 23 && fd != 0 && fd != -1)
    std::abort();
  const auto *p = static_cast<const char *>(data);
  if (n == 1 && *p == '?') {
    event("char 63");
    return 1;
  }
  if (n == 2 && p[0] == '\r' && p[1] == '\n') {
    event("send " + hex(writing));
    writing.clear();
  } else
    writing.append(p, n);
  return n;
}
extern "C" ssize_t __wrap_read(int fd, void *data, std::size_t n) {
  if ((fd != 23 && fd != 0 && fd != -1) || n != 1)
    std::abort();
  if (pending.empty()) {
    const std::string next =
        responseIndex < responses.size() ? responses[responseIndex++] : "0";
    if (next.empty()) {
      emptyClock = true;
      return 0;
    }
    pending = next + "\n";
  }
  *static_cast<char *>(data) = pending.front();
  pending.erase(0, 1);
  return 1;
}
extern "C" int __wrap_open(const char *path, int, ...) {
  event("open " + std::string(path));
  return portSuccess ? 23 : -1;
}
extern "C" int __wrap_close(int fd) {
  event("close " + std::to_string(fd));
  return 0;
}
extern "C" int __wrap_tcgetattr(int, termios *p) {
  std::memset(p, 0, sizeof(*p));
  return 0;
}
extern "C" int __wrap_tcsetattr(int, int, const termios *) { return 0; }
extern "C" int __wrap_tcflush(int, int) { return 0; }
extern "C" int __wrap_clock_gettime(clockid_t, timespec *t) {
  t->tv_sec = emptyClock ? 202 : clockMilliseconds / 1000;
  t->tv_nsec = (clockMilliseconds % 1000) * 1000000;
  emptyClock = false;
  return 0;
}
extern "C" int __wrap_usleep(useconds_t n) {
  event("sleep " + std::to_string(n / 1000));
  return 0;
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == deleting)
    event("delete");
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  if (p == deleting)
    event("delete");
  __real__ZdlPvm(p, n);
}
int main(int argc, char **argv) {
  if (argc != 13)
    return 2;
  std::string method = argv[1];
  unsigned size = std::stoul(argv[2]), a = std::stoul(argv[3]),
           b = std::stoul(argv[4]), d = std::stoul(argv[5]);
  unsigned first = std::stoul(argv[6]), sectors = std::stoul(argv[7]),
           destination = std::stoul(argv[8]);
  if (method == "printProgress")
    clockMilliseconds = d;
  bool listener = std::stoi(argv[9]);
  portSuccess = std::stoi(argv[10]);
  std::string text = argv[11], variant = argv[12];
  unsigned n;
  std::cin >> n;
  std::string line;
  std::getline(std::cin, line);
  for (unsigned i = 0; i < n; ++i) {
    std::getline(std::cin, line);
    responses.push_back(line);
  }
  std::vector<unsigned char> image(70000);
  for (unsigned i = 0; i < image.size(); ++i)
    image[i] = method == "raw" ? (a == 0   ? 0
                                  : a == 1 ? 255
                                           : (i * 37 + 11) & 255)
                               : (i * 37 + 11) & 255;
  auto *p = new Presonus::LPCProgrammer(image.data(), size);
  Listener sink;
  p->imageState.raw30 = first;
  p->imageState.raw48 = sectors;
  p->imageState.raw34 = destination;
  p->imageState.raw18 = 620761368;
  p->imageState.raw38 = 7;
  p->imageState.raw40 = first;
  p->imageState.raw4c = 4096;
  p->deviceIdentity.raw1c_to28 = {1, 2, 3, 4};
  p->deviceIdentity.raw2c = 123;
  p->listener = listener ? &sink : nullptr;
  current104_test::seedLpcStartMilliseconds();
  capture = true;
  int result = 0;
  bool hasReturn = true;
  if (method == "raw") {
    std::array<unsigned char, 1024> out;
    out.fill(0xa5);
    result = current104_test::lpcRawEncode(out.data(), size, image.data());
    event("output " + hex(out.data(), 260));
  } else if (method == "ctor") {
    auto *q = new Presonus::LPCProgrammer(image.data(), size);
    event("state " + std::to_string(q->imageState.raw08) + " " +
          std::to_string(q->inputState.descriptor) + " " +
          std::to_string(q->baudRate) + " 0 " +
          std::to_string(q->imageState.raw18) + " " +
          std::to_string(q->imageState.raw30) + " " +
          std::to_string(q->imageState.raw34) + " " +
          std::to_string(q->ramAddress) + " " +
          std::to_string(q->commandTimeout));
    hasReturn = false;
    capture = false;
    delete q;
    capture = true;
  } else if (method == "dtor") {
    if (variant.find("D0") != std::string::npos) {
      deleting = p;
      delete p;
      deleting = nullptr;
    } else {
      p->~LPCProgrammer();
      ::operator delete(p);
    }
    p = nullptr;
    hasReturn = false;
  } else if (method == "open")
    result = p->open(text.c_str());
  else if (method == "printInfo") {
    p->printInfo();
    hasReturn = false;
  } else if (method == "printProgress") {
    p->printProgress(text.c_str());
    hasReturn = false;
  } else if (method == "unlockFlash")
    result = p->unlockFlash();
  else if (method == "eraseSector")
    result = p->eraseSector(a, b);
  else if (method == "prepareSector")
    result = p->prepareSector(a, b);
  else if (method == "copyRAM2Flash")
    result = p->copyRAM2Flash(a, b, d);
  else if (method == "eraseAll")
    result = p->eraseAll();
  else if (method == "writeRAM")
    result = p->writeRAM(0x10000400, size, image.data());
  else if (method == "update") {
    result = p->update(listener ? &sink : nullptr);
    event("block " + hex(p->block.data(), 512));
  } else
    return 3;
  if (hasReturn)
    event("ret " + std::to_string(result));
  capture = false;
  if (p)
    delete p;
  for (auto &s : events)
    std::cout << "@" << s << "\n";
}
