#include "presonus/mixer_dsp/AdditionalFormatters.hpp"
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <new>
#include <string>
using Gain = Presonus::Dsp::GainFormatter;
using Pan = Presonus::Dsp::PanFormatter;
extern "C" void gainC1(Gain *, int,
                       bool) asm("_ZN8Presonus3Dsp13GainFormatterC1Eib");
extern "C" void gainC2(Gain *, int,
                       bool) asm("_ZN8Presonus3Dsp13GainFormatterC2Eib");
extern "C" void gainD1(Gain *) asm("_ZN8Presonus3Dsp13GainFormatterD1Ev");
extern "C" void gainD0(Gain *) asm("_ZN8Presonus3Dsp13GainFormatterD0Ev");
extern "C" void
panC1(Pan *, Pan::Mode) asm("_ZN8Presonus3Dsp12PanFormatterC1ENS1_4ModeE");
extern "C" void
panC2(Pan *, Pan::Mode) asm("_ZN8Presonus3Dsp12PanFormatterC2ENS1_4ModeE");
extern "C" void panD1(Pan *) asm("_ZN8Presonus3Dsp12PanFormatterD1Ev");
extern "C" void panD0(Pan *) asm("_ZN8Presonus3Dsp12PanFormatterD0Ev");
extern "C" void *__real__Znwm(std::size_t);
extern "C" void __real__ZdlPv(void *) noexcept;
extern "C" void __real__ZdlPvm(void *, std::size_t) noexcept;
namespace observation {
struct Allocation {
  void *pointer;
  std::size_t size;
  bool alive;
  unsigned sized, unsized, forwarded;
};
Allocation allocations[50000]{};
unsigned count = 0;
bool capture = false;
Allocation *find(void *p) {
  for (unsigned i = count; i > 0; --i)
    if (allocations[i - 1].pointer == p && allocations[i - 1].alive)
      return &allocations[i - 1];
  return nullptr;
}
} // namespace observation
extern "C" void *__wrap__Znwm(std::size_t size) {
  void *p = __real__Znwm(size);
  if (observation::capture) {
    assert(observation::count < 50000);
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
__attribute__((noinline)) void deleteBase(Core::Formatter *p) { delete p; }
__attribute__((noinline)) void virtualBehavior(Core::Formatter *p, bool gain,
                                               int value, bool label) {
  char text[128]{};
  Core::Formatter::Data d{nullptr, text, 128, gain ? 12.75f : .25f, nullptr};
  p->print(d);
  if (gain) {
    const char *values[] = {"13", "12.8", "12.75"};
    std::string expected = values[value];
    if (label)
      expected += " dB";
    assert(expected == text);
    char input[] = "12.75";
    d.string = input;
    assert(p->scan(d) && d.value == 12.75f);
  } else {
    assert(std::strcmp(text, value == 1 ? "L 50" : "L 25") == 0);
    char input[] = "12.75";
    d.string = input;
    d.value = -123.f;
    assert(!p->scan(d) && d.value == -123.f);
  }
}
unsigned lifecycle = 0, dispatches = 0, explicitD1 = 0, explicitD0 = 0,
         baseDeletes = 0, typedDeletes = 0;
template <class T, class Construct>
void exercise(Construct construct, const std::string &expected, void (*d1)(T *),
              void (*d0)(T *), bool gain, int value, bool label) {
  for (unsigned variant = 0; variant < 3; ++variant)
    for (unsigned destruction = 0; destruction < 4; ++destruction) {
      observation::capture = true;
      T *p = static_cast<T *>(::operator new(sizeof(T)));
      unsigned index = observation::count - 1;
      construct(p, variant);
      observation::capture = false;
      const char *name = p->getName();
      assert(expected == "null" ? name == nullptr : name && expected == name);
      // Inspect the live native table only; no original ARM layout/vptr claim.
      std::uintptr_t table = 0;
      std::memcpy(&table, p, sizeof(table));
      std::uintptr_t slots[2];
      std::memcpy(slots, reinterpret_cast<const void *>(table), sizeof(slots));
      assert(slots[0] == reinterpret_cast<std::uintptr_t>(d1) &&
             slots[1] == reinterpret_cast<std::uintptr_t>(d0));
      if ((gain && value >= 0 && value <= 2) ||
          (!gain && (value == 0 || value == 1))) {
        virtualBehavior(p, gain, value, label);
        ++dispatches;
      }
      if (destruction == 0) {
        d1(p);
        assert(observation::allocations[index].alive);
        ::operator delete(p);
        ++explicitD1;
      } else if (destruction == 1) {
        d0(p);
        ++explicitD0;
      } else if (destruction == 2) {
        deleteBase(p);
        ++baseDeletes;
      } else {
        delete p;
        ++typedDeletes;
      }
      const auto &allocation = observation::allocations[index];
      assert(!allocation.alive && allocation.forwarded == 1 &&
             allocation.sized + allocation.unsized == 1);
      ++lifecycle;
    }
}
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream input(argv[1]);
  assert(input);
  char kind;
  int value, label;
  std::string encoded;
  unsigned names = 0;
  while (input >> kind >> value >> label >> encoded) {
    std::string expected = encoded == "null" ? "null" : "";
    if (encoded != "null")
      for (std::size_t i = 0; i < encoded.size(); i += 2)
        expected +=
            static_cast<char>(std::stoul(encoded.substr(i, 2), nullptr, 16));
    if (kind == 'G') {
      const char *name = Gain::nameFromPrecision(value, label != 0);
      assert(expected == "null" ? name == nullptr : name && expected == name);
      exercise<Gain>(
          [&](Gain *p, unsigned variant) {
            if (variant == 0)
              gainC1(p, value, label != 0);
            else if (variant == 1)
              gainC2(p, value, label != 0);
            else
              new (p) Gain(value, label != 0);
          },
          expected, gainD1, gainD0, true, value, label != 0);
    } else {
      assert(kind == 'P');
      auto mode = static_cast<Pan::Mode>(value);
      const char *name = Pan::nameFromMode(mode);
      assert(name && expected == name);
      exercise<Pan>(
          [&](Pan *p, unsigned variant) {
            if (variant == 0)
              panC1(p, mode);
            else if (variant == 1)
              panC2(p, mode);
            else
              new (p) Pan(mode);
          },
          expected, panD1, panD0, false, value, false);
    }
    ++names;
  }
  assert(input.eof() && names > 3000 && lifecycle == 12 * names &&
         observation::count == lifecycle);
  unsigned sized = 0, unsized = 0;
  for (unsigned i = 0; i < observation::count; ++i) {
    const auto &a = observation::allocations[i];
    assert(!a.alive && a.forwarded == 1);
    sized += a.sized;
    unsized += a.unsized;
  }
  std::cout << "{\"passed\":true,\"name_cases\":" << names
            << ",\"lifecycle_cases\":" << lifecycle
            << ",\"virtual_dispatches\":" << dispatches
            << ",\"explicit_d1\":" << explicitD1
            << ",\"actual_d0\":" << explicitD0
            << ",\"base_deletes\":" << baseDeletes
            << ",\"typed_deletes\":" << typedDeletes
            << ",\"real_allocations\":" << observation::count
            << ",\"sized_deletes\":" << sized
            << ",\"unsized_deletes\":" << unsized
            << ",\"all_released\":true}\n";
}
