#ifdef NDEBUG
#undef NDEBUG
#endif
#include "presonus/mixer_dsp/GateMeterInterpolators.hpp"
#include <cassert>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <new>
using Gate = Presonus::Dsp::GateRangeInterpolator;
using Meter = Presonus::Dsp::MeterCurveInterpolator;
extern "C" void
GateC1(Gate *) asm("_ZN8Presonus3Dsp21GateRangeInterpolatorC1Ev");
extern "C" void
GateC2(Gate *) asm("_ZN8Presonus3Dsp21GateRangeInterpolatorC2Ev");
extern "C" void
GateD1(Gate *) asm("_ZN8Presonus3Dsp21GateRangeInterpolatorD1Ev");
extern "C" void
GateD0(Gate *) asm("_ZN8Presonus3Dsp21GateRangeInterpolatorD0Ev");
extern "C" void
MeterC1(Meter *) asm("_ZN8Presonus3Dsp22MeterCurveInterpolatorC1Ev");
extern "C" void
MeterC2(Meter *) asm("_ZN8Presonus3Dsp22MeterCurveInterpolatorC2Ev");
extern "C" void
MeterD1(Meter *) asm("_ZN8Presonus3Dsp22MeterCurveInterpolatorD1Ev");
extern "C" void
MeterD0(Meter *) asm("_ZN8Presonus3Dsp22MeterCurveInterpolatorD0Ev");
extern "C" void *__real__Znwm(std::size_t);
extern "C" void *__real__Znam(std::size_t);
extern "C" void __real__ZdlPv(void *) noexcept;
extern "C" void __real__ZdlPvm(void *, std::size_t) noexcept;
extern "C" void __real__ZdaPv(void *) noexcept;
extern "C" void __real__ZdaPvm(void *, std::size_t) noexcept;
namespace observation {
enum class Kind { none, curve, points };
struct Allocation {
  void *pointer;
  std::size_t size;
  Kind kind;
  bool alive;
  unsigned sized, unsized, forwarded;
};
Allocation records[128]{};
unsigned count = 0;
Kind watching = Kind::none;
Allocation *find(void *p) {
  for (unsigned i = 0; i < count; ++i)
    if (records[i].pointer == p && records[i].alive)
      return &records[i];
  return nullptr;
}
void allocated(void *p, std::size_t size) {
  if (watching != Kind::none) {
    assert(count < 128);
    records[count++] = {p, size, watching, true, 0, 0, 0};
  }
}
} // namespace observation
extern "C" void *__wrap__Znwm(std::size_t size) {
  void *p = __real__Znwm(size);
  observation::allocated(p, size);
  return p;
}
extern "C" void *__wrap__Znam(std::size_t size) {
  void *p = __real__Znam(size);
  observation::allocated(p, size);
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
extern "C" void __wrap__ZdaPv(void *p) noexcept {
  auto *a = observation::find(p);
  if (a)
    ++a->unsized;
  __real__ZdaPv(p);
  if (a) {
    a->alive = false;
    ++a->forwarded;
  }
}
extern "C" void __wrap__ZdaPvm(void *p, std::size_t size) noexcept {
  auto *a = observation::find(p);
  if (a) {
    assert(a->size == size);
    ++a->sized;
  }
  __real__ZdaPvm(p, size);
  if (a) {
    a->alive = false;
    ++a->forwarded;
  }
}

__attribute__((noinline)) void deleteRoot(Core::Interpolator *p) { delete p; }
__attribute__((noinline)) void deleteSegment(Core::SegmentInterpolator *p) {
  delete p;
}
template <class T> __attribute__((noinline)) void deleteTyped(T *p) {
  delete p;
}
__attribute__((noinline)) float forward(Core::Interpolator *p, float x) {
  return p->normalizedToRange(x);
}
__attribute__((noinline)) float reverse(Core::Interpolator *p, float x) {
  return p->rangeToNormalized(x);
}
unsigned cases = 0, liveChecks = 0;
template <class T>
void exercise(void (*c1)(T *), void (*c2)(T *), void (*d1)(T *),
              void (*d0)(T *), float lo, float hi) {
  for (unsigned ctor = 1; ctor <= 3; ++ctor)
    for (unsigned destruction = 0; destruction < 5; ++destruction) {
      observation::watching = observation::Kind::curve;
      T *p = static_cast<T *>(::operator new(sizeof(T)));
      observation::watching = observation::Kind::none;
      unsigned record = observation::count - 1;
      if (ctor == 3)
        new (p) T();
      else
        (ctor == 1 ? c1 : c2)(p);
      auto **vt = *reinterpret_cast<void ***>(p);
      assert(vt[0] == reinterpret_cast<void *>(d1));
      assert(vt[1] == reinterpret_cast<void *>(d0));
      assert(std::fabs(forward(p, 0) - lo) < 1.e-6f &&
             std::fabs(forward(p, 1) - hi) < 1.e-6f);
      assert(std::fabs(reverse(p, lo)) < 1.e-6f &&
             std::fabs(reverse(p, hi) - 1.f) < 1.e-6f);
      for (float x : {.07f, .14f, .21f, .29f, .36f, .43f, .5f, .57f, .64f, .71f,
                      .76f, .89f, .93f}) {
        float value = forward(p, x);
        assert(value >= lo && value <= hi);
        float roundtrip = reverse(p, value);
        assert(roundtrip >= x - 0.000001f && roundtrip <= x + 0.000001f);
        ++liveChecks;
      }
      if (destruction == 0) {
        d1(p);
        assert(observation::records[record].alive);
        ::operator delete(p);
      } else if (destruction == 1)
        d0(p);
      else if (destruction == 2)
        deleteRoot(p);
      else if (destruction == 3)
        deleteSegment(p);
      else
        deleteTyped(p);
      assert(!observation::records[record].alive &&
             observation::records[record].forwarded == 1);
      ++cases;
    }
}
int main() {
  exercise<Gate>(GateC1, GateC2, GateD1, GateD0, -84.f, 0.f);
  exercise<Meter>(MeterC1, MeterC2, MeterD1, MeterD0, 6.30957344e-8f,
                  3.16227766f);
  unsigned sized = 0, unsized = 0;
  for (unsigned i = 0; i < observation::count; ++i) {
    auto &a = observation::records[i];
    assert(!a.alive && a.forwarded == 1);
    sized += a.sized;
    unsized += a.unsized;
  }
  assert(cases == 30 && liveChecks == 390 && sized == 24 && unsized == 6);
  std::cout << "{\"passed\":true,\"cases\":" << cases
            << ",\"live_checks\":" << liveChecks
            << ",\"sized_deletes\":" << sized
            << ",\"unsized_deletes\":" << unsized << "}\n";
}
