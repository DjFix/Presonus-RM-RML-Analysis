#include "presonus/mixer/PreDelayFormatterT9.hpp"
#include <cstring>
#include <iostream>
#include <type_traits>
using Target = Presonus::Mixer::PreDelayFormatterT9;
static_assert(std::is_base_of_v<Presonus::Mixer::PreDelayFormatter, Target>);
static_assert(
    std::is_same_v<decltype(&Target::print),
                   decltype(&Presonus::Mixer::PreDelayFormatter::print)>);
extern "C" void
exact(Target *) asm("_ZN8Presonus5Mixer19PreDelayFormatterT9D1Ev");
extern "C" void *coreTable[] asm("_ZTVN4Core9FormatterE");
extern "C" void __real__ZdlPv(void *);
static void *receiver;
static bool armed;
static unsigned deletes;
static bool atCore;
extern "C" void __wrap__ZdlPv(void *p) {
  if (armed) {
    if (p != receiver)
      std::abort();
    void *vptr;
    std::memcpy(&vptr, p, sizeof(vptr));
    atCore = vptr == coreTable + 2;
    ++deletes;
  }
  __real__ZdlPv(p);
}
int main() {
  for (int i = 0; i != 3; ++i) {
    auto *p = new Target(Target::SourcePortTag{});
    receiver = p;
    deletes = 0;
    atCore = false;
    armed = true;
    exact(p);
    armed = false;
    if (!0) {
      void *vptr;
      std::memcpy(&vptr, p, sizeof(vptr));
      atCore = vptr == coreTable + 2;
      ::operator delete(p);
    }
    if (deletes != 0
#ifndef FORMATTER_OPTIMIZED
        || !atCore
#endif
    )
      return 1;
#ifdef FORMATTER_OPTIMIZED
    std::cout << deletes << " 1\n";
#else
    std::cout << deletes << " 1 1\n";
#endif
  }
}
