#ifdef NDEBUG
#undef NDEBUG
#endif
#include "presonus/mixer_dsp/FaderCurveInterpolator.hpp"
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <new>
using Curve = Presonus::Dsp::FaderCurveInterpolator;
using Point = Core::SegmentInterpolator::BreakPoint;
extern "C" void
curveC1(Curve *) asm("_ZN8Presonus3Dsp22FaderCurveInterpolatorC1Ev");
extern "C" void
curveC2(Curve *) asm("_ZN8Presonus3Dsp22FaderCurveInterpolatorC2Ev");
extern "C" void customC1(Curve *, int, const Point *) asm(
    "_ZN8Presonus3Dsp22FaderCurveInterpolatorC1EiPKN4Co"
    "re19SegmentInterpolator10BreakPointE");
extern "C" void customC2(Curve *, int, const Point *) asm(
    "_ZN8Presonus3Dsp22FaderCurveInterpolatorC2EiPKN4Co"
    "re19SegmentInterpolator10BreakPointE");
extern "C" void
curveD1(Curve *) asm("_ZN8Presonus3Dsp22FaderCurveInterpolatorD1Ev");
extern "C" void
curveD0(Curve *) asm("_ZN8Presonus3Dsp22FaderCurveInterpolatorD0Ev");
extern "C" float curveForward(const Curve *, float) asm(
    "_ZNK8Presonus3Dsp22FaderCurveInterpolator17normalizedToRangeEf");
extern "C" float curveReverse(const Curve *, float) asm(
    "_ZNK8Presonus3Dsp22FaderCurveInterpolator17rangeToNormalizedEf");
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
namespace {
std::uint32_t bits(float f) {
  std::uint32_t word;
  std::memcpy(&word, &f, 4);
  return word;
}
__attribute__((noinline)) void deleteRoot(Core::Interpolator *p) { delete p; }
__attribute__((noinline)) void deleteSegment(Core::SegmentInterpolator *p) {
  delete p;
}
__attribute__((noinline)) void deleteDerived(Curve *p) { delete p; }
__attribute__((noinline)) float forward(Core::Interpolator *p, float value) {
  return p->normalizedToRange(value);
}
__attribute__((noinline)) float reverse(Core::Interpolator *p, float value) {
  return p->rangeToNormalized(value);
}
__attribute__((noinline)) void inheritedSet(Core::Interpolator *p) {
  p->setRange(-999.f, 999.f, 7.f);
}
struct Case {
  unsigned configuration, variant, destruction, count;
  bool borrowedMutation, callerAlive;
};
} // namespace
int main() {
  Case cases[40]{};
  unsigned caseCount = 0, mutations = 0, callerChecks = 0;
  const Point defaultPoints[5] = {
      {0, -144}, {.04f, -60}, {.16f, -40}, {.52f, -10}, {1, 10}};
  for (unsigned configuration = 0; configuration < 4; ++configuration)
    for (unsigned variant = 1; variant <= 2; ++variant)
      for (unsigned destruction = 0; destruction < 5; ++destruction) {
        const bool custom = configuration != 0;
        const unsigned count = configuration == 1   ? 2
                               : configuration == 2 ? 3
                                                    : 5;
        Point *points = nullptr;
        unsigned pointRecord = 0;
        if (custom) {
          observation::watching = observation::Kind::points;
          points = new Point[count];
          observation::watching = observation::Kind::none;
          pointRecord = observation::count - 1;
          if (count == 2) {
            points[0] = {0, -145};
            points[1] = {1, -143};
          } else if (count == 3) {
            points[0] = {0, -160};
            points[1] = {.5f, -20};
            points[2] = {1, 12};
          } else
            for (unsigned i = 0; i < count; ++i)
              points[i] = defaultPoints[i];
        }
        observation::watching = observation::Kind::curve;
        void *storage = ::operator new(sizeof(Curve));
        observation::watching = observation::Kind::none;
        const unsigned curveRecord = observation::count - 1;
        auto *object = static_cast<Curve *>(storage);
        if (custom) {
          if (variant == 1)
            customC1(object, static_cast<int>(count), points);
          else
            customC2(object, static_cast<int>(count), points);
        } else {
          if (variant == 1)
            curveC1(object);
          else
            curveC2(object);
        }
        const Point *expected = custom ? points : defaultPoints;
        assert(bits(object->getMinRange()) == bits(expected[0].range));
        assert(bits(object->getMaxRange()) == bits(expected[count - 1].range));
        assert(object->getMidRange() == 1.f && object->getName() == nullptr);
        assert(bits(object->normalizedToDb(0.f)) == bits(expected[0].range));
        assert(bits(object->normalizedToDb(1.f)) ==
               bits(expected[count - 1].range));
        auto **table = *reinterpret_cast<void ***>(object);
        assert(table[0] == reinterpret_cast<void *>(curveD1));
        assert(table[1] == reinterpret_cast<void *>(curveD0));
        assert(table[3] == reinterpret_cast<void *>(curveForward));
        assert(table[4] == reinterpret_cast<void *>(curveReverse));
        assert(bits(forward(object, .5f)) ==
               bits(object->Curve::normalizedToRange(.5f)));
        assert(bits(reverse(object, 1.f)) ==
               bits(object->Curve::rangeToNormalized(1.f)));
        const float minimum = object->getMinRange(),
                    maximum = object->getMaxRange();
        inheritedSet(object);
        assert(object->getMinRange() == minimum &&
               object->getMaxRange() == maximum &&
               object->getMidRange() == 1.f);
        bool mutated = false;
        if (custom && count >= 3) {
          const auto index = count / 2;
          points[index].range -= 4.f;
          assert(bits(object->normalizedToDb(points[index].normalized)) ==
                 bits(points[index].range));
          mutated = true;
          ++mutations;
        }
        auto &allocation = observation::records[curveRecord];
        assert(allocation.alive && allocation.kind == observation::Kind::curve);
        if (destruction == 0) {
          curveD1(object);
          assert(allocation.alive && allocation.forwarded == 0);
          ::operator delete(storage);
        } else if (destruction == 1)
          curveD0(object);
        else if (destruction == 2)
          deleteRoot(object);
        else if (destruction == 3)
          deleteSegment(object);
        else
          deleteDerived(object);
        assert(!allocation.alive && allocation.forwarded == 1 &&
               allocation.sized + allocation.unsized == 1);
        bool callerAlive = false;
        if (custom) {
          auto &buffer = observation::records[pointRecord];
          assert(buffer.alive && buffer.kind == observation::Kind::points &&
                 buffer.forwarded == 0);
          callerAlive = true;
          ++callerChecks;
          points[0].range = 123.f;
          assert(points[0].range == 123.f);
          delete[] points;
          assert(!buffer.alive && buffer.forwarded == 1 &&
                 buffer.sized + buffer.unsized == 1);
        }
        cases[caseCount++] = {configuration, variant, destruction,
                              count,         mutated, callerAlive};
      }
  unsigned curveAllocations = 0, pointAllocations = 0, curveSized = 0,
           curveUnsized = 0, pointSized = 0, pointUnsized = 0;
  for (unsigned i = 0; i < observation::count; ++i) {
    const auto &r = observation::records[i];
    assert(!r.alive && r.forwarded == 1);
    if (r.kind == observation::Kind::curve) {
      ++curveAllocations;
      curveSized += r.sized;
      curveUnsized += r.unsized;
    } else {
      ++pointAllocations;
      pointSized += r.sized;
      pointUnsized += r.unsized;
    }
  }
  assert(caseCount == 40 && curveAllocations == 40 && pointAllocations == 30 &&
         mutations == 20 && callerChecks == 30);
  std::cout << "{\"passed\":true,\"cases\":" << caseCount
            << ",\"curve_allocations\":" << curveAllocations
            << ",\"caller_array_allocations\":" << pointAllocations
            << ",\"curve_sized_delete\":" << curveSized
            << ",\"curve_unsized_delete\":" << curveUnsized
            << ",\"array_sized_delete\":" << pointSized
            << ",\"array_unsized_delete\":" << pointUnsized
            << ",\"borrowed_mutation_observations\":" << mutations
            << ",\"caller_arrays_alive_after_curve_cleanup\":" << callerChecks
            << ",\"all_recorded_allocations_released\":true,\"post_lifetime_"
               "vptr_compared\":false,\"records\":[";
  for (unsigned i = 0; i < caseCount; ++i) {
    if (i)
      std::cout << ',';
    const auto &c = cases[i];
    std::cout << "[" << c.configuration << ',' << c.variant << ','
              << c.destruction << ',' << c.count << ','
              << (c.borrowedMutation ? "true" : "false") << ','
              << (c.callerAlive ? "true" : "false") << "]";
  }
  std::cout << "]}" << std::endl;
}
