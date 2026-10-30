#ifdef NDEBUG
#undef NDEBUG
#endif
#include "presonus/mixer_dsp/AdditionalFormatters.hpp"
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <new>
extern "C" void
millisecondsC1(void *, const char *,
               bool) asm("_ZN8Presonus3Dsp21MillisecondsFormatterC1EPKcb");
extern "C" void
millisecondsC2(void *, const char *,
               bool) asm("_ZN8Presonus3Dsp21MillisecondsFormatterC2EPKcb");
extern "C" void
millisecondsD1(void *) asm("_ZN8Presonus3Dsp21MillisecondsFormatterD1Ev");
extern "C" void
millisecondsD0(void *) asm("_ZN8Presonus3Dsp21MillisecondsFormatterD0Ev");
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
__attribute__((noinline)) bool dispatch(Core::Formatter *object,
                                        bool precision) {
  Core::Formatter::Range range{0, 100};
  char text[128]{};
  Core::Formatter::Data d{nullptr, text, 128, 1.25f, &range};
  object->print(d);
  if (std::strcmp(text, precision ? "1.250 ms" : "1.2 ms"))
    return false;
  std::strcpy(text, "2");
  if (!object->scan(d))
    return false;
  return d.value == 2.f;
}
__attribute__((noinline)) void virtualDelete(Core::Formatter *object) {
  delete object;
}
int main() {
  using Presonus::Dsp::MillisecondsFormatter;
  unsigned cases = 0, mutations = 0;
  for (unsigned ctor : {1u, 2u})
    for (bool precision : {false, true})
      for (unsigned label : {0u, 1u, 2u, 3u})
        for (unsigned destruction : {0u, 1u, 2u}) {
          char borrowed[128]{};
          std::strcpy(borrowed, label == 2   ? "latency"
                                : label == 3 ? "borrowed"
                                             : "");
          const char *name = label == 0 ? nullptr : borrowed;
          observation::capture = true;
          void *storage = ::operator new(sizeof(MillisecondsFormatter));
          observation::capture = false;
          auto &allocation = observation::allocations[observation::count - 1];
          (ctor == 1 ? millisecondsC1 : millisecondsC2)(storage, name,
                                                        precision);
          auto *base = static_cast<Core::Formatter *>(
              static_cast<MillisecondsFormatter *>(storage));
          assert(base->getName() == name);
          if (name) {
            assert(std::strcmp(base->getName(), borrowed) == 0);
            std::strcpy(borrowed, "changed");
            assert(std::strcmp(base->getName(), "changed") == 0);
            ++mutations;
          }
          assert(dispatch(base, precision));
          auto **vtable = *reinterpret_cast<void ***>(storage);
          assert(vtable[0] == reinterpret_cast<void *>(millisecondsD1));
          assert(vtable[1] == reinterpret_cast<void *>(millisecondsD0));
          if (destruction == 0) {
            millisecondsD1(storage);
            assert(allocation.alive && allocation.forwarded == 0);
            ::operator delete(storage);
          } else if (destruction == 1)
            millisecondsD0(storage);
          else
            virtualDelete(base);
          assert(!allocation.alive && allocation.forwarded == 1 &&
                 allocation.sized + allocation.unsized == 1);
          ++cases;
        }
  unsigned sized = 0, unsized = 0;
  for (unsigned i = 0; i < observation::count; ++i) {
    auto &a = observation::allocations[i];
    assert(!a.alive);
    sized += a.sized;
    unsized += a.unsized;
  }
  std::cout << "{\"passed\":true,\"cases\":" << cases
            << ",\"label_mutations\":" << mutations
            << ",\"real_allocations\":" << observation::count
            << ",\"forwarded_sized_delete\":" << sized
            << ",\"forwarded_unsized_delete\":" << unsized
            << ",\"all_allocations_released\":true}" << std::endl;
}
