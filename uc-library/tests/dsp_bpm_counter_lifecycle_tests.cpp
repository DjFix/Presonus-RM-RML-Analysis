#ifdef NDEBUG
#undef NDEBUG
#endif
#include "presonus/mixer_dsp/AdditionalFormatters.hpp"
#include <cassert>
#include <climits>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <new>
static_assert(sizeof(int) == 4);
extern "C" void bpmC1(Presonus::Dsp::BPMFormatter *,
                      bool) asm("_ZN8Presonus3Dsp12BPMFormatterC1Eb");
extern "C" void bpmC2(Presonus::Dsp::BPMFormatter *,
                      bool) asm("_ZN8Presonus3Dsp12BPMFormatterC2Eb");
extern "C" void
bpmD1(Presonus::Dsp::BPMFormatter *) asm("_ZN8Presonus3Dsp12BPMFormatterD1Ev");
extern "C" void
bpmD0(Presonus::Dsp::BPMFormatter *) asm("_ZN8Presonus3Dsp12BPMFormatterD0Ev");
extern "C" void counterC1(Presonus::Dsp::CounterFormatter *,
                          int) asm("_ZN8Presonus3Dsp16CounterFormatterC1Ei");
extern "C" void counterC2(Presonus::Dsp::CounterFormatter *,
                          int) asm("_ZN8Presonus3Dsp16CounterFormatterC2Ei");
extern "C" void counterD1(Presonus::Dsp::CounterFormatter *) asm(
    "_ZN8Presonus3Dsp16CounterFormatterD1Ev");
extern "C" void counterD0(Presonus::Dsp::CounterFormatter *) asm(
    "_ZN8Presonus3Dsp16CounterFormatterD0Ev");
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
Allocation allocations[128]{};
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
    assert(observation::count < 128);
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
__attribute__((noinline)) bool dispatch(Core::Formatter *object, bool counter,
                                        int config) {
  char text[128]{};
  Core::Formatter::Range range{0, 100};
  Core::Formatter::Data d{nullptr, text, 128, counter ? 12.75f : 1.25f, &range};
  object->print(d);
  const char *expected = counter ? (config == 8   ? "00000012"
                                    : config == 3 ? "012"
                                                  : "12")
                                 : (config ? "1.25 BPM" : "1.25");
  if (std::strcmp(text, expected))
    return false;
  std::strcpy(text, counter ? "12345" : "12.75");
  if (!object->scan(d))
    return false;
  return d.value == (counter ? 12345.f : 12.75f);
}
__attribute__((noinline)) void deleteBase(Core::Formatter *object) {
  delete object;
}
__attribute__((noinline)) void deleteBpm(Presonus::Dsp::BPMFormatter *object) {
  delete object;
}
__attribute__((noinline)) void
deleteCounter(Presonus::Dsp::CounterFormatter *object) {
  delete object;
}
int main() {
  using namespace Presonus::Dsp;
  unsigned cases = 0, ordinary = 0, ctorOnly = 0;
  const int counterConfigs[] = {0, 1, 3, 8, -1, INT_MIN, INT_MAX};
  for (bool counter : {false, true})
    for (unsigned configIndex = 0; configIndex < (counter ? 7u : 2u);
         ++configIndex)
      for (unsigned ctor : {1u, 2u})
        for (unsigned destruction = 0; destruction < 4; ++destruction) {
          const int config = counter ? counterConfigs[configIndex]
                                     : static_cast<int>(configIndex);
          const bool ordinaryValid = !counter || configIndex < 4;
          observation::capture = true;
          void *storage = ::operator new(counter ? sizeof(CounterFormatter)
                                                 : sizeof(BPMFormatter));
          observation::capture = false;
          auto &allocation = observation::allocations[observation::count - 1];
          if (counter) {
            if (ctor == 1)
              counterC1(static_cast<CounterFormatter *>(storage), config);
            else
              counterC2(static_cast<CounterFormatter *>(storage), config);
          } else {
            if (ctor == 1)
              bpmC1(static_cast<BPMFormatter *>(storage), config != 0);
            else
              bpmC2(static_cast<BPMFormatter *>(storage), config != 0);
          }
          Core::Formatter *base =
              counter ? static_cast<Core::Formatter *>(
                            static_cast<CounterFormatter *>(storage))
                      : static_cast<Core::Formatter *>(
                            static_cast<BPMFormatter *>(storage));
          assert(std::strcmp(base->getName(), counter  ? "count"
                                              : config ? "bpm"
                                                       : "bpm.value") == 0);
          auto **vtable = *reinterpret_cast<void ***>(storage);
          assert(vtable[0] == (counter ? reinterpret_cast<void *>(counterD1)
                                       : reinterpret_cast<void *>(bpmD1)));
          assert(vtable[1] == (counter ? reinterpret_cast<void *>(counterD0)
                                       : reinterpret_cast<void *>(bpmD0)));
          if (ordinaryValid) {
            assert(dispatch(base, counter, config));
            ++ordinary;
          } else
            ++ctorOnly;
          if (destruction == 0) {
            if (counter)
              counterD1(static_cast<CounterFormatter *>(storage));
            else
              bpmD1(static_cast<BPMFormatter *>(storage));
            assert(allocation.alive && allocation.forwarded == 0);
            ::operator delete(storage);
          } else if (destruction == 1) {
            if (counter)
              counterD0(static_cast<CounterFormatter *>(storage));
            else
              bpmD0(static_cast<BPMFormatter *>(storage));
          } else if (destruction == 2)
            deleteBase(base);
          else {
            if (counter)
              deleteCounter(static_cast<CounterFormatter *>(storage));
            else
              deleteBpm(static_cast<BPMFormatter *>(storage));
          }
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
  assert(cases == 72 && ordinary == 48 && ctorOnly == 24 && sized == 54 &&
         unsized == 18);
  std::cout << "{\"passed\":true,\"cases\":" << cases
            << ",\"real_allocations\":" << observation::count
            << ",\"forwarded_sized_delete\":" << sized
            << ",\"forwarded_unsized_delete\":" << unsized
            << ",\"all_allocations_released\":true,\"ordinary_dispatch_cases\":"
            << ordinary << ",\"invalid_width_ctor_only_cases\":" << ctorOnly
            << ",\"typed_bool_and_int_ctor_arguments\":true,\"post_lifetime_"
               "vptr_compared\":false}"
            << std::endl;
}
