#include "presonus/surface/LCDPort.hpp"
#include <array>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unistd.h>
using Port = Presonus::Surface::LCDPort;
static bool failDevices = false, captureBuffer = false;
static void *object = nullptr;
static void *buffer = nullptr;
static unsigned deleted = 0, freed = 0, reallocated = 0;
static FILE *projectFile() {
  const char *dir = std::getenv("TMPDIR");
  if (!dir || std::string(dir).find(
                  "/home/rs/projects/opencs/ai-line-analysis/temp/") != 0)
    throw std::runtime_error("project TMPDIR required");
  std::string path = std::string(dir) + "/lcd-offline-XXXXXX";
  int fd = mkstemp(path.data());
  if (fd < 0)
    throw std::runtime_error("project file creation");
  return fdopen(fd, "w+b");
}
extern "C" FILE *__wrap_fopen(const char *path, const char *) {
  if (std::string(path).find("/sys/class/gpio/") != 0 &&
      std::string(path) != "offline-frame")
    throw std::runtime_error("unexpected file path");
  return projectFile();
}
extern "C" int __wrap_open(const char *path, int, ...) {
  if (std::string(path).find("/dev/spidev1.") != 0)
    throw std::runtime_error("unexpected device path");
  return failDevices ? -1 : 47;
}
extern "C" int __wrap_close(int fd) {
  if (fd != 47)
    throw std::runtime_error("unexpected fd");
  return 0;
}
extern "C" int __wrap_ioctl(int fd, unsigned long, ...) {
  if (fd != 47)
    throw std::runtime_error("unexpected ioctl fd");
  return -1;
}
extern "C" void __wrap__ZN4Core8Platform13CurrentThread5sleepEj(unsigned) {}
extern "C" void *__real_core_realloc(void *, unsigned);
extern "C" void __real_core_free(void *);
extern "C" void *__wrap_core_realloc(void *p, unsigned n) {
  void *result = __real_core_realloc(p, n);
  if (captureBuffer) {
    if (p || n != 8 || !result)
      throw std::runtime_error("actual Buffer allocation");
    buffer = result;
    ++reallocated;
  }
  return result;
}
extern "C" void __wrap_core_free(void *p) {
  if (buffer && p == buffer)
    ++freed;
  __real_core_free(p);
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == object)
    ++deleted;
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  if (p == object)
    ++deleted;
  __real__ZdlPvm(p, n);
}
extern "C" void C1(Port *) asm("_ZN8Presonus7Surface7LCDPortC1Ev");
extern "C" void C2(Port *) asm("_ZN8Presonus7Surface7LCDPortC2Ev");
extern "C" void D1(Port *) asm("_ZN8Presonus7Surface7LCDPortD1Ev");
extern "C" void D2(Port *) asm("_ZN8Presonus7Surface7LCDPortD2Ev");
extern "C" void D0(Port *) asm("_ZN8Presonus7Surface7LCDPortD0Ev");
int main() {
  unsigned cases = 0;
  for (int ctor = 0; ctor != 2; ++ctor)
    for (int variant = 0; variant != 3; ++variant)
      for (bool withBuffer : {false, true})
        for (bool failed : {false, true}) {
          failDevices = failed;
          deleted = freed = reallocated = 0;
          buffer = nullptr;
          void *allocation = ::operator new(sizeof(Port));
          auto *p = static_cast<Port *>(allocation);
          if (ctor)
            C2(p);
          else
            C1(p);
          Presonus::IDisplayPort *base = p;
          if (base->isDisplayBufferActive(nullptr) ||
              base->isDisplayBufferActive(allocation) ||
              base->sendDisplayCommands(255, nullptr, -1) != 0)
            throw std::runtime_error("real port fixed methods");
          if (withBuffer) {
            std::array<unsigned char, 16> pixels{};
            Core::BitmapData data;
            data.width = 2;
            data.height = 2;
            data.rowBytes = 8;
            data.scan0 = pixels.data();
            data.bitsPerPixel = 32;
            captureBuffer = true;
            bool result = p->write("offline-frame", data);
            captureBuffer = false;
            if (!result || reallocated != 1 || !buffer)
              throw std::runtime_error("actual buffered transfer");
          }
          object = p;
          if (variant == 0)
            D1(p);
          else if (variant == 1)
            D2(p);
          else
            D0(p);
          if (deleted != unsigned(variant == 2) ||
              freed != unsigned(withBuffer))
            throw std::runtime_error("actual cleanup/deallocation");
          object = nullptr;
          buffer = nullptr;
          if (variant != 2)
            ::operator delete(allocation);
          ++cases;
        }
  std::cout
      << "{\"passed\":true,\"cases\":" << cases
      << ",\"actual_Buffer_allocation_free\":true,\"actual_D0_delete\":true}\n";
}
