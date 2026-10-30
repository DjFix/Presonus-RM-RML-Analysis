#ifdef NDEBUG
#undef NDEBUG
#endif
#include "presonus/mixer_dsp/Formatters.hpp"
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <new>
extern "C" void freqC1(Presonus::Dsp::FreqFormatter *,
                       bool) asm("_ZN8Presonus3Dsp13FreqFormatterC1Eb");
extern "C" void freqC2(Presonus::Dsp::FreqFormatter *,
                       bool) asm("_ZN8Presonus3Dsp13FreqFormatterC2Eb");
extern "C" void freqD1(Presonus::Dsp::FreqFormatter *) asm(
    "_ZN8Presonus3Dsp13FreqFormatterD1Ev");
extern "C" void freqD0(Presonus::Dsp::FreqFormatter *) asm(
    "_ZN8Presonus3Dsp13FreqFormatterD0Ev");
extern "C" void gainC1(Presonus::Dsp::GainDBFormatter *,
                       bool) asm("_ZN8Presonus3Dsp15GainDBFormatterC1Eb");
extern "C" void gainC2(Presonus::Dsp::GainDBFormatter *,
                       bool) asm("_ZN8Presonus3Dsp15GainDBFormatterC2Eb");
extern "C" void gainD1(Presonus::Dsp::GainDBFormatter *) asm(
    "_ZN8Presonus3Dsp15GainDBFormatterD1Ev");
extern "C" void gainD0(Presonus::Dsp::GainDBFormatter *) asm(
    "_ZN8Presonus3Dsp15GainDBFormatterD0Ev");
extern "C" void *__real__Znwm(std::size_t);
extern "C" void __real__ZdlPv(void *) noexcept;
extern "C" void __real__ZdlPvm(void *, std::size_t) noexcept;
namespace observation {
struct Allocation {
  void *pointer;
  std::size_t size;
  bool alive;
  unsigned unsized;
  unsigned sized;
  unsigned forwarded;
};
Allocation allocations[64]{};
unsigned count = 0;
bool capture = false;
Allocation *find(void *p) {
  for (unsigned i = 0; i < count; ++i)
    if (allocations[i].pointer == p && allocations[i].alive)
      return &allocations[i];
  return nullptr;
}
} // namespace observation
extern "C" void *__wrap__Znwm(std::size_t size) {
  void *p = __real__Znwm(size);
  if (observation::capture) {
    assert(observation::count < 64);
    observation::allocations[observation::count++] = {p, size, true, 0, 0, 0};
  }
  return p;
}
extern "C" void __wrap__ZdlPv(void *p) noexcept {
  auto *a = observation::find(p);
  if (a)
    ++a->unsized;
  __real__ZdlPv(p);
  if (a) {
    a->alive = false;
    ++a->forwarded;
  }
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) noexcept {
  auto *a = observation::find(p);
  if (a) {
    assert(a->size == size);
    ++a->sized;
  }
  __real__ZdlPvm(p, size);
  if (a) {
    a->alive = false;
    ++a->forwarded;
  }
}
__attribute__((noinline)) bool dispatch(Core::Formatter *object, bool gain,
                                        bool option) {
  char text[128]{};
  Core::Formatter::Range range{0, 100};
  Core::Formatter::Data d{nullptr, text, 128, 1.25f, &range};
  object->print(d);
  const char *expected =
      gain ? (option ? "+1.9 dB" : "+1.9") : (option ? "1 Hz" : "1.25 Hz");
  if (std::strcmp(text, expected))
    return false;
  std::strcpy(text, gain ? "0" : "2k");
  if (!object->scan(d))
    return false;
  return d.value == (gain ? 1.f : 2000.f);
}
__attribute__((noinline)) void virtualDelete(Core::Formatter *object) {
  delete object;
}
int main() {
  using namespace Presonus::Dsp;
  unsigned cases = 0;
  for (bool gain : {false, true})
    for (bool option : {false, true})
      for (unsigned ctor : {1u, 2u})
        for (unsigned destruction : {0u, 1u, 2u}) {
          observation::capture = true;
          void *storage = ::operator new(gain ? sizeof(GainDBFormatter)
                                              : sizeof(FreqFormatter));
          observation::capture = false;
          auto &allocation = observation::allocations[observation::count - 1];
          if (gain) {
            if (ctor == 1)
              gainC1(static_cast<GainDBFormatter *>(storage), option);
            else
              gainC2(static_cast<GainDBFormatter *>(storage), option);
          } else {
            if (ctor == 1)
              freqC1(static_cast<FreqFormatter *>(storage), option);
            else
              freqC2(static_cast<FreqFormatter *>(storage), option);
          }
          Core::Formatter *base =
              gain ? static_cast<Core::Formatter *>(
                         static_cast<GainDBFormatter *>(storage))
                   : static_cast<Core::Formatter *>(
                         static_cast<FreqFormatter *>(storage));
          const char *name = gain ? (option ? "gain.db" : "gain.db.value")
                                  : (option ? "freq.0" : "freq");
          assert(std::strcmp(base->getName(), name) == 0);
          assert(dispatch(base, gain, option));
          auto **vtable = *reinterpret_cast<void ***>(storage);
          assert(vtable[0] == (gain ? reinterpret_cast<void *>(gainD1)
                                    : reinterpret_cast<void *>(freqD1)));
          assert(vtable[1] == (gain ? reinterpret_cast<void *>(gainD0)
                                    : reinterpret_cast<void *>(freqD0)));
          if (destruction == 0) {
            if (gain)
              gainD1(static_cast<GainDBFormatter *>(storage));
            else
              freqD1(static_cast<FreqFormatter *>(storage));
            assert(allocation.alive && allocation.forwarded == 0);
            ::operator delete(storage);
          } else if (destruction == 1) {
            if (gain)
              gainD0(static_cast<GainDBFormatter *>(storage));
            else
              freqD0(static_cast<FreqFormatter *>(storage));
          } else
            virtualDelete(base);
          assert(!allocation.alive && allocation.forwarded == 1 &&
                 allocation.sized + allocation.unsized == 1);
          ++cases;
        }
  unsigned sized = 0, unsized = 0;
  for (unsigned i = 0; i < observation::count; ++i) {
    const auto &a = observation::allocations[i];
    assert(!a.alive);
    sized += a.sized;
    unsized += a.unsized;
  }
  std::cout << "{\"passed\":true,\"cases\":" << cases
            << ",\"real_allocations\":" << observation::count
            << ",\"forwarded_sized_delete\":" << sized
            << ",\"forwarded_unsized_delete\":" << unsized
            << ",\"all_allocations_released\":true,\"typed_bool_constructor_"
               "arguments\":true,\"original_core_behavior_verified\":false}"
            << std::endl;
}
