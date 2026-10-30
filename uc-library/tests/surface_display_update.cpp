#include "presonus/surface/LCDPort.hpp"
#include <cstdarg>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <linux/spi/spidev.h>
#include <stdexcept>
#include <string>
#include <vector>

#include <cstdlib>
#include <unistd.h>
static FILE *projectTemporaryFile() {
  const char *dir = std::getenv("TMPDIR");
  if (!dir || std::string(dir).find(
                  "/home/rs/projects/opencs/ai-line-analysis/temp/") != 0)
    throw std::runtime_error("project TMPDIR required");
  std::string path = std::string(dir) + "/offline-file-XXXXXX";
  int fd = mkstemp(path.data());
  if (fd < 0)
    throw std::runtime_error("project temp creation failed");
  return fdopen(fd, "w+b");
}
static bool openFail = false;
static bool ioctlFail = false;
static std::string trace;
extern "C" int __wrap_open(const char *path, int, ...) {
  if (std::string(path).find("/dev/spidev1.") != 0)
    throw std::runtime_error("unexpected path");
  return openFail ? -1 : 47;
}
extern "C" int __wrap_close(int fd) {
  if (fd != 47)
    throw std::runtime_error("unexpected descriptor");
  return 0;
}
extern "C" FILE *__wrap_fopen(const char *path, const char *) {
  if (std::string(path) == "/dev/fb0")
    return projectTemporaryFile();
  if (std::string(path).find("/sys/class/gpio/") != 0)
    throw std::runtime_error("unexpected GPIO");
  return projectTemporaryFile();
}
extern "C" void __wrap__ZN4Core8Platform13CurrentThread5sleepEj(unsigned) {}
extern "C" int __wrap_ioctl(int fd, unsigned long request, ...) {
  if (fd != 47 || request != SPI_IOC_MESSAGE(1))
    throw std::runtime_error("unexpected ioctl");
  va_list a;
  va_start(a, request);
  auto *t = va_arg(a, spi_ioc_transfer *);
  va_end(a);
  if (t->rx_buf || t->speed_hz || t->delay_usecs || t->bits_per_word ||
      t->cs_change)
    throw std::runtime_error("transfer fields");
  auto *p = reinterpret_cast<unsigned char *>(t->tx_buf);
  const char *h = "0123456789abcdef";
  for (unsigned i = 0; i < t->len; ++i) {
    trace += h[p[i] >> 4];
    trace += h[p[i] & 15];
  }
  trace += ':';
  return ioctlFail ? -1 : static_cast<int>(t->len);
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  Presonus::Surface::LCDPort mgr;
  std::ifstream in(argv[1]);
  int mode, display, stride, command, length, of, io, expectedResult;
  std::string hex, want;
  unsigned count = 0;
  while (in >> mode >> display >> stride >> command >> length >> of >> io >>
         expectedResult >> hex >> want) {
    std::vector<unsigned char> pixels;
    for (unsigned i = 0; i < hex.size(); i += 2)
      pixels.push_back(std::stoul(hex.substr(i, 2), nullptr, 16));
    Core::BitmapData b;
    b.width = 64;
    b.height = 96;
    b.rowBytes = stride;
    b.scan0 = pixels.data();
    openFail = of;
    ioctlFail = io;
    trace.clear();
    if (mode == 0) {
      Presonus::DisplayUpdate update{static_cast<unsigned char>(display + 1),
                                     &b};
      int result = mgr.updateDisplay(update);
      if (result != expectedResult)
        throw std::runtime_error("return differs");
    } else if (mode == 1)
      throw std::runtime_error("unexpected fixture mode");
    else if (mode == 2)
      throw std::runtime_error("unexpected fixture mode");
    else {
      throw std::runtime_error("unexpected fixture mode");
    }
    if (trace != (want == "-" ? "" : want))
      throw std::runtime_error("SPI byte sequence differs");
    ++count;
  }
  std::cout << "{\"passed\":true,\"cases\":" << count << "}\n";
}
