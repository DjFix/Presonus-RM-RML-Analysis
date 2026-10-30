#include "presonus/mixer_dsp/FaderInterpolator.hpp"
#include <cassert>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <new>
using Fader = Presonus::Dsp::FaderInterpolator;
using Point = Core::SegmentInterpolator::BreakPoint;
static const Point customPoints[5] = {
    {0, 0}, {.25f, 1}, {.5f, 2}, {.75f, 3}, {1, 4}};
namespace presonus::dsp {
struct FaderInterpolatorSourceAccess {
  struct State {
    std::uint32_t minimum, maximum, middle;
    const Point *points;
    int count;
  };
  static std::uint32_t bits(const float &value) {
    std::uint32_t word;
    std::memcpy(&word, &value, 4);
    return word;
  }
  static State snapshot(const Fader &value) {
    return {bits(value.minRange), bits(value.maxRange), bits(value.midRange),
            value.breakPoints, value.numPoints};
  }
  // Independent valid nonowning test fixtures, never production fallback state.
  static void useCurve(Fader &value, const Point *points) {
    value.breakPoints = points;
    value.numPoints = 5;
  }
};
} // namespace presonus::dsp
using Access = presonus::dsp::FaderInterpolatorSourceAccess;
extern "C" void faderC1(Fader *) asm("_ZN8Presonus3Dsp17FaderInterpolatorC1Ev");
extern "C" void faderC2(Fader *) asm("_ZN8Presonus3Dsp17FaderInterpolatorC2Ev");
extern "C" void faderD1(Fader *) asm("_ZN8Presonus3Dsp17FaderInterpolatorD1Ev");
extern "C" void faderD0(Fader *) asm("_ZN8Presonus3Dsp17FaderInterpolatorD0Ev");
extern "C" void
faderSet(Fader *, float, float,
         float) asm("_ZN8Presonus3Dsp17FaderInterpolator8setRangeEfff");
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
Allocation allocations[128]{};
unsigned count = 0;
bool capture = false;
Allocation *find(void *p) {
  for (unsigned n = count; n > 0; --n)
    if (allocations[n - 1].pointer == p && allocations[n - 1].alive)
      return &allocations[n - 1];
  return nullptr;
}
void borrowedNeverFreed(void *p) {
  assert(p != Fader::kCurvePoints84 && p != Fader::kCurvePoints96 &&
         p != customPoints);
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
  observation::borrowedNeverFreed(p);
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
  observation::borrowedNeverFreed(p);
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
const Point *curve(unsigned mode) {
  assert(mode < 3);
  return mode == 0   ? Fader::kCurvePoints84
         : mode == 1 ? Fader::kCurvePoints96
                     : customPoints;
}
float fromWord(std::uint32_t word) {
  float value;
  std::memcpy(&value, &word, 4);
  return value;
}
__attribute__((noinline)) void dispatch(Core::Interpolator &object, float a,
                                        float b, float c) {
  object.setRange(a, b, c);
}
__attribute__((noinline)) void deleteBase(Core::Interpolator *object) {
  delete object;
}
void nativeTargets(const Fader &object) {
  std::uintptr_t table = 0;
  std::memcpy(&table, &object, sizeof(table));
  std::uintptr_t slots[3];
  std::memcpy(slots, reinterpret_cast<const void *>(table), sizeof(slots));
  assert(slots[0] == reinterpret_cast<std::uintptr_t>(faderD1) &&
         slots[1] == reinterpret_cast<std::uintptr_t>(faderD0) &&
         slots[2] == reinterpret_cast<std::uintptr_t>(faderSet));
}
unsigned lifecycle() {
  unsigned count = 0;
  for (unsigned variant = 0; variant < 3; ++variant)
    for (unsigned mode = 0; mode < 3; ++mode)
      for (unsigned destruction = 0; destruction < 4; ++destruction) {
        observation::capture = true;
        auto *p = static_cast<Fader *>(::operator new(sizeof(Fader)));
        unsigned index = observation::count - 1;
        if (variant == 0)
          faderC1(p);
        else if (variant == 1)
          faderC2(p);
        else
          new (p) Fader;
        observation::capture = false;
        auto state = Access::snapshot(*p);
        assert(state.minimum == Access::bits(Fader::kCurvePoints84[0].range) &&
               state.maximum == Access::bits(Fader::kCurvePoints84[4].range) &&
               state.middle == 0x3f800000u &&
               state.points == Fader::kCurvePoints84 && state.count == 5 &&
               p->getName() == nullptr);
        nativeTargets(*p);
        Access::useCurve(*p, curve(mode));
        if (destruction == 0) {
          faderD1(p);
          assert(observation::allocations[index].alive);
          ::operator delete(p);
        } else if (destruction == 1)
          faderD0(p);
        else if (destruction == 2)
          deleteBase(p);
        else
          delete p;
        auto &allocation = observation::allocations[index];
        assert(!allocation.alive && allocation.forwarded == 1 &&
               allocation.sized + allocation.unsized == 1);
        ++count;
      }
  return count;
}
unsigned realCoreCurveContract() {
  unsigned count = 0;
  Fader fader;
  for (unsigned mode = 0; mode < 2; ++mode) {
    const auto *points = curve(mode);
    dispatch(fader, points[0].range, points[4].range, 1.f);
    assert(Access::snapshot(fader).points == points);
    for (unsigned i = 0; i <= 4096; ++i) {
      float n = static_cast<float>(i) / 4096.f;
      float value = fader.normalizedToRange(n);
      assert(std::isfinite(value) && value >= points[0].range &&
             value <= points[4].range);
      float back = fader.rangeToNormalized(value);
      assert(std::fabs(back - n) < 2.e-6f);
      ++count;
    }
    for (unsigned i = 0; i < 5; ++i) {
      assert(std::fabs(fader.normalizedToRange(points[i].normalized) -
                       points[i].range) < 1.e-5f);
      assert(std::fabs(fader.rangeToNormalized(points[i].range) -
                       points[i].normalized) < 1.e-6f);
    }
  }
  // This verifies actual pinned-source behavior, not original Core execution.
  Core::SegmentInterpolator base(5, Fader::kCurvePoints84);
  base.setRange(-96.f, 99.f, 7.f);
  assert(base.getMinRange() == -84.f && base.getMaxRange() == 10.f &&
         base.getMidRange() == 1.f);
  return count;
}
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream input(argv[1]);
  assert(input);
  Fader object;
  std::uint32_t minimum, maximum, middle;
  unsigned initial, expected, cases = 0;
  while (input >> minimum >> maximum >> middle >> initial >> expected) {
    Access::useCurve(object, curve(initial));
    dispatch(object, fromWord(minimum), fromWord(maximum), fromWord(middle));
    auto state = Access::snapshot(object);
    assert(state.minimum == minimum && state.maximum == maximum &&
           state.middle == middle && state.points == curve(expected) &&
           state.count == 5);
    ++cases;
  }
  assert(input.eof() && cases > 10000);
  unsigned lifetimes = lifecycle();
  assert(lifetimes == 36 && observation::count == 36);
  unsigned sized = 0, unsized = 0;
  for (unsigned i = 0; i < observation::count; ++i) {
    auto &a = observation::allocations[i];
    assert(!a.alive && a.forwarded == 1);
    sized += a.sized;
    unsized += a.unsized;
  }
  unsigned coreSamples = realCoreCurveContract();
  std::cout << "{\"passed\":true,\"setter_cases\":" << cases
            << ",\"lifetimes\":" << lifetimes
            << ",\"real_allocations\":" << observation::count
            << ",\"sized_deletes\":" << sized
            << ",\"unsized_deletes\":" << unsized
            << ",\"all_released\":true,\"static_arrays_never_deleted\":true,"
               "\"real_core_source_curve_samples\":"
            << coreSamples
            << ",\"core_segment_setrange_noop_observed\":true}\n";
}
