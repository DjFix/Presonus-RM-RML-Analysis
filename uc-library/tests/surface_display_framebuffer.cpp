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
static FILE *frameFile;
static bool failFrame;
extern "C" FILE *__wrap_fopen(const char *path, const char *) {
  if (std::string(path) == "/dev/fb0")
    return failFrame ? nullptr : (frameFile = projectTemporaryFile());
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
static std::string expectedFrame;
static unsigned frameCloses = 0;
extern "C" int __real_fclose(FILE *);
extern "C" int __wrap_fclose(FILE *file) {
  if (file == frameFile) {
    std::fflush(file);
    std::fseek(file, 0, SEEK_END);
    long size = std::ftell(file);
    std::rewind(file);
    std::string bytes(size, '\0');
    std::fread(bytes.data(), 1, bytes.size(), file);
    if (bytes != expectedFrame)
      throw std::runtime_error("framebuffer bytes differ");
    frameFile = nullptr;
    ++frameCloses;
  }
  return __real_fclose(file);
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  Presonus::Surface::LCDPort port;
  std::ifstream in(argv[1]);
  int w, h, stride;
  std::string hex, want;
  unsigned cases = 0;
  while (in >> w >> h >> stride >> hex >> want) {
    std::vector<unsigned char> pixels;
    for (unsigned i = 0; i < hex.size(); i += 2)
      pixels.push_back(std::stoul(hex.substr(i, 2), nullptr, 16));
    expectedFrame.clear();
    if (want != "-")
      for (unsigned i = 0; i < want.size(); i += 2)
        expectedFrame.push_back(
            static_cast<char>(std::stoul(want.substr(i, 2), nullptr, 16)));
    Core::BitmapData b;
    b.width = w;
    b.height = h;
    b.rowBytes = stride;
    b.scan0 = pixels.data();
    Presonus::DisplayUpdate update{0, &b};
    for (bool fail : {false, true}) {
      failFrame = fail;
      unsigned before = frameCloses;
      if (port.updateDisplay(update) != 1)
        throw std::runtime_error("original always-one return differs");
      if (frameCloses - before != unsigned(!fail))
        throw std::runtime_error("frame cleanup differs");
      ++cases;
    }
  }
  std::cout << "{\"passed\":true,\"cases\":" << cases << "}\n";
}
