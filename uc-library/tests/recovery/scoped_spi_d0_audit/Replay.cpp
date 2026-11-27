#include "presonus/panel/SPIControl.hpp"
#include <cstdio>
#include <cstdlib>
#include <new>
namespace {
void *watched = nullptr;
int deletes = 0;
int sizedDeletes = 0;
std::size_t allocationSize = 0;
int baseEntries = 0;
bool allocated = false;
} // namespace
extern "C" void *__real__Znwm(std::size_t);
extern "C" void *__wrap__Znwm(std::size_t size) {
  void *p = __real__Znwm(size);
  if (allocated) {
    if (watched)
      std::abort();
    watched = p;
    allocationSize = size;
  }
  return p;
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == watched && p) {
    if (baseEntries != 1)
      std::abort();
    ++deletes;
    watched = nullptr;
  }
  __real__ZdlPv(p);
}
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  if (p == watched && p) {
    if (baseEntries != 1 || size != allocationSize)
      std::abort();
    ++deletes;
    ++sizedDeletes;
    watched = nullptr;
  }
  __real__ZdlPvm(p, size);
}
extern "C" void realBase(void *) asm("__real__ZN8Presonus5Panel7ControlD2Ev");
extern "C" void wrapBase(void *) asm("__wrap__ZN8Presonus5Panel7ControlD2Ev");
extern "C" void wrapBase(void *p) {
  if (p == watched)
    ++baseEntries;
  realBase(p);
}
[[gnu::noipa]] void destroy(Presonus::Panel::Control *p) { delete p; }
int main() {
  const int cases[][3] = {{4, 0, 0},
                          {-5, 7, -1},
                          {0, -1, 17},
                          {-2147483647 - 1, 2147483647, -100},
                          {2147483647, -2147483647 - 1, 1}};
  for (auto &args : cases) {
    if (presonus::panel::ControlAccess::timers().count() != 0)
      std::abort();
    deletes = 0;
    sizedDeletes = 0;
    baseEntries = 0;
    allocated = true;
    auto *p = new Presonus::Panel::SPIControl(args[0], args[1], args[2]);
    allocated = false;
    if (p != watched || p->getParameter() || p->getAltParameter() ||
        p->getTertiaryParameter())
      std::abort();
    destroy(p);
    if (presonus::panel::ControlAccess::timers().count() != 0)
      std::abort();
    if (watched || deletes != 1 || baseEntries != 1)
      std::abort();
    std::printf("%d %d %d\n", baseEntries, deletes, watched == nullptr);
    std::fprintf(stderr,
                 "sized_deletes=%d unsized_deletes=%d allocation_size=%zu\n",
                 sizedDeletes, deletes - sizedDeletes, allocationSize);
  }
}
