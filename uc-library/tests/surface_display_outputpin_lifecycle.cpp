#include "presonus/surface_panel/OutputPin.hpp"
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <new>
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
using Pin = Presonus::Panel::OutputPin;
using Access = presonus::surface_panel_port::OutputPinAccess;
static bool failOpen = false;
static void *watched = nullptr;
static unsigned deletes = 0, closes = 0;
static std::vector<FILE *> opened;
extern "C" FILE *__wrap_fopen(const char *path, const char *) {
  if (std::string(path).find("/sys/class/gpio/") != 0)
    throw std::runtime_error("unexpected path");
  if (failOpen)
    return nullptr;
  FILE *f = projectTemporaryFile();
  opened.push_back(f);
  return f;
}
extern "C" int __real_fclose(FILE *);
extern "C" int __wrap_fclose(FILE *f) {
  if (f == nullptr)
    throw std::runtime_error("null fclose");
  ++closes;
  return __real_fclose(f);
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == watched)
    ++deletes;
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  if (p == watched)
    ++deletes;
  __real__ZdlPvm(p, n);
}
extern "C" void C1(Pin *, int) asm("_ZN8Presonus5Panel9OutputPinC1Ei");
extern "C" void C2(Pin *, int) asm("_ZN8Presonus5Panel9OutputPinC2Ei");
extern "C" void D1(Pin *) asm("_ZN8Presonus5Panel9OutputPinD1Ev");
extern "C" void D2(Pin *) asm("_ZN8Presonus5Panel9OutputPinD2Ev");
extern "C" void D0(Pin *) asm("_ZN8Presonus5Panel9OutputPinD0Ev");
int main() {
  unsigned cases = 0;
  for (int ctor = 0; ctor != 2; ++ctor)
    for (int variant = 0; variant != 3; ++variant)
      for (int pin : {-1, 0, 29, 30})
        for (bool failure : {false, true}) {
          failOpen = failure;
          closes = 0;
          deletes = 0;
          void *memory = ::operator new(sizeof(Pin));
          auto *p = static_cast<Pin *>(memory);
          if (ctor)
            C2(p, pin);
          else
            C1(p, pin);
          if (Access::number(*p) != pin || Access::state(*p) != -1)
            throw std::runtime_error("constructor fields");
          bool hasFile = pin >= 0 && !failure;
          if (bool(Access::file(*p)) != hasFile)
            throw std::runtime_error("constructor file");
          unsigned before = closes;
          watched = memory;
          if (variant == 0)
            D1(p);
          else if (variant == 1)
            D2(p);
          else
            D0(p);
          if (closes - before != unsigned(hasFile))
            throw std::runtime_error("destructor close");
          if (deletes != unsigned(variant == 2))
            throw std::runtime_error("actual deallocation count");
          watched = nullptr;
          if (variant != 2)
            ::operator delete(memory);
          ++cases;
        }
  std::cout << "{\"passed\":true,\"cases\":" << cases
            << ",\"C1_C2_called_directly\":true,\"D1_D2_D0_called_directly\":"
               "true,\"actual_operator_delete_observed\":true}\n";
}
