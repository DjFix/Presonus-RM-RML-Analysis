#ifdef NDEBUG
#undef NDEBUG
#endif
#include "presonus/mixer_dsp/EqParameterLists.hpp"
#include "presonus/mixer_dsp/EqSourceProviders.hpp"
#include <cassert>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
using Eq = Presonus::Dsp::EqParamList;
using Ext = Presonus::Dsp::Eq8ExtParamList;
extern "C" void EqC1(Eq *) asm("_ZN8Presonus3Dsp11EqParamListC1Ev");
extern "C" void EqC2(Eq *) asm("_ZN8Presonus3Dsp11EqParamListC2Ev");
extern "C" void EqD1(Eq *) asm("_ZN8Presonus3Dsp11EqParamListD1Ev");
extern "C" void ExtC1(Ext *) asm("_ZN8Presonus3Dsp15Eq8ExtParamListC1Ev");
extern "C" void ExtC2(Ext *) asm("_ZN8Presonus3Dsp15Eq8ExtParamListC2Ev");
extern "C" void ExtD1(Ext *) asm("_ZN8Presonus3Dsp15Eq8ExtParamListD1Ev");
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
Allocation records[16384]{};
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
    assert(count < 16384);
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

extern "C" int __real___cxa_atexit(void (*)(void *), void *, void *);
struct Callback {
  void (*function)(void *);
  void *object;
  unsigned sequence;
};
Callback callbacks[16]{};
unsigned callbackCount = 0, sequence = 0;
bool captureCallbacks = false;
extern "C" int __wrap___cxa_atexit(void (*f)(void *), void *p, void *dso) {
  ++sequence;
  if (captureCallbacks) {
    assert(callbackCount < 16);
    callbacks[callbackCount++] = {f, p, sequence};
  }
  return __real___cxa_atexit(f, p, dso);
}
unsigned lifecycleCases = 0, descriptorObservations = 0,
         mainAllocationCount = 0;
bool bootstrapped = false;
void allReleased(unsigned begin = 0) {
  for (unsigned i = begin; i < observation::count; ++i)
    assert(!observation::records[i].alive &&
           observation::records[i].forwarded == 1);
}
void exitObserver() {
  allReleased();
  unsigned sized = 0, unsized = 0;
  for (unsigned i = 0; i < observation::count; ++i) {
    sized += observation::records[i].sized;
    unsized += observation::records[i].unsized;
  }
  std::printf("{\"passed\":true,\"exit_observer\":true,\"bootstrapped\":%s,"
              "\"real_allocations\":%u,\"actual_sized_deletes\":%u,\"actual_"
              "unsized_deletes\":%u,\"all_released\":true}\n",
              bootstrapped ? "true" : "false", observation::count, sized,
              unsized);
}
void inspect(const Presonus::Dsp::ParamDescriptorList &list, const char *cls,
             unsigned count, bool emit) {
  assert(list.sourceCount() == static_cast<int>(count));
  for (unsigned i = 0; i < count; ++i) {
    auto *p = list.getAt(static_cast<int>(i));
    assert(p);
    const auto &st = p->sourceState();
    assert(st.tag == static_cast<int>(i));
    assert(st.word18 == 32);
    if (emit)
      std::printf(
          "{\"fixture\":true,\"class\":\"%s\",\"index\":%u,\"tag\":%d,"
          "\"flags\":%u,\"word10\":%u,\"word14\":%u,\"word18\":%u,\"text0\":\"%"
          "s\",\"text1\":\"%s\",\"text2\":\"%s\",\"formatter\":%s,\"formatter_"
          "name\":\"%s\",\"interpolator\":%s,\"interpolator_name\":\"%s\"}\n",
          cls, i, st.tag, st.flags, st.word10, st.word14, st.word18,
          st.text0.str(), st.text1.str(), st.text2.str(),
          st.formatter ? "true" : "false",
          st.formatter ? st.formatter->getName() : "",
          st.interpolator ? "true" : "false",
          st.interpolator && st.interpolator->getName()
              ? st.interpolator->getName()
              : "");
    if (bootstrapped && st.interpolator) {
      float x = st.interpolator->normalizedToRange(.5f);
      assert(std::isfinite(x));
      const float normalized = st.interpolator->rangeToNormalized(x);
      assert(std::isfinite(normalized) && normalized >= 0.f &&
             normalized <= 1.f);
    }
    ++descriptorObservations;
  }
}
template <class T>
void exercise(const char *cls, unsigned count, void (*c1)(T *), void (*c2)(T *),
              void (*d1)(T *)) {
  for (unsigned variant = 0; variant < 3; ++variant)
    for (unsigned destruction = 0; destruction < 2; ++destruction) {
      unsigned begin = observation::count;
      observation::watching = observation::Kind::curve;
      T *p = static_cast<T *>(::operator new(sizeof(T)));
      const unsigned owner = observation::count - 1;
      if (variant == 0)
        c1(p);
      else if (variant == 1)
        c2(p);
      else
        new (p) T;
      inspect(presonus::dsp::sourceList(*p), cls, count,
              variant == 0 && destruction == 0);
      if (destruction == 0) {
        d1(p);
        assert(observation::records[owner].alive);
        ::operator delete(p);
      } else
        delete p;
      observation::watching = observation::Kind::none;
      allReleased(begin);
      ++lifecycleCases;
    }
}
int main(int argc, char **argv) {
  bootstrapped = argc > 1 && std::strcmp(argv[1], "bootstrap") == 0;
  assert(!presonus::dsp::eqSourcePortProvidersReady());
  // Warm source CCL registries before bootstrap callback/lifetime observation.
  Core::FormatterRegistry::find("");
  delete Core::InterpolatorFactory::create("linear");
  if (bootstrapped) {
    captureCallbacks = true;
    presonus::dsp::registerEqSourcePortProviders();
    captureCallbacks = false;
    assert(presonus::dsp::eqSourcePortProvidersReady());
    assert(callbackCount >= 1);
  } else
    assert(!Core::FormatterRegistry::find("gain") &&
           !Core::FormatterRegistry::find("freq") &&
           !Core::FormatterRegistry::find("eqq"));
  exercise<Eq>("EqParamList", 25, EqC1, EqC2, EqD1);
  exercise<Ext>("Eq8ExtParamList", 49, ExtC1, ExtC2, ExtD1);
  assert(lifecycleCases == 12 && descriptorObservations == 444);
  allReleased();
  mainAllocationCount = observation::count;
  std::atexit(exitObserver);
  if (bootstrapped) {
    const unsigned before = callbackCount;
    captureCallbacks = true;
    observation::watching = observation::Kind::curve;
    auto *eq = Eq::instance();
    auto *ext = Ext::instance();
    observation::watching = observation::Kind::none;
    captureCallbacks = false;
    assert(Eq::instance() == eq && Ext::instance() == ext &&
           callbackCount == before + 2);
    assert(callbacks[before].function ==
               reinterpret_cast<void (*)(void *)>(EqD1) &&
           callbacks[before].object == eq);
    assert(callbacks[before + 1].function ==
               reinterpret_cast<void (*)(void *)>(ExtD1) &&
           callbacks[before + 1].object == ext);
    assert(callbacks[0].sequence < callbacks[before].sequence &&
           callbacks[0].sequence < callbacks[before + 1].sequence);
    inspect(presonus::dsp::sourceList(*eq), "EqParamList", 25, false);
    inspect(presonus::dsp::sourceList(*ext), "Eq8ExtParamList", 49, false);
  }
  if (bootstrapped) {
    auto *eq = Eq::instance();
    std::printf("{\"callback_records\":[");
    for (unsigned i = 0; i < callbackCount; ++i) {
      auto functionDelta = static_cast<long long>(
          reinterpret_cast<std::intptr_t>(callbacks[i].function) -
          reinterpret_cast<std::intptr_t>(EqD1));
      auto objectDelta = static_cast<long long>(
          reinterpret_cast<std::intptr_t>(callbacks[i].object) -
          reinterpret_cast<std::intptr_t>(eq));
      std::printf("%s{\"sequence\":%u,\"function_from_eq_d1\":%lld,\"object_"
                  "from_eq_instance\":%lld}",
                  i ? "," : "", callbacks[i].sequence, functionDelta,
                  objectDelta);
    }
    std::printf("]}\n");
  }
  std::cout << "{\"passed\":true,\"lifecycle_cases\":" << lifecycleCases
            << ",\"descriptor_observations\":" << descriptorObservations
            << ",\"bootstrapped\":" << (bootstrapped ? "true" : "false")
            << ",\"main_allocations\":" << mainAllocationCount
            << ",\"singleton_callbacks\":" << (bootstrapped ? 2 : 0)
            << ",\"unchanged_callbacks_forwarded\":true}\n";
}
