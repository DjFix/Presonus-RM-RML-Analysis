#include "presonus/mixer_dsp/GEQParameterList.hpp"
#include "presonus/mixer_dsp/GEQSourceProviders.hpp"
#include <cassert>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
using Comp = Presonus::Dsp::GEQParamList;
extern "C" void compC1(Comp *) asm("_ZN8Presonus3Dsp12GEQParamListC1Ev");
extern "C" void compC2(Comp *) asm("_ZN8Presonus3Dsp12GEQParamListC2Ev");
extern "C" void compD1(Comp *) asm("_ZN8Presonus3Dsp12GEQParamListD1Ev");
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
    if (emit) {
      const auto bits = [](float value) {
        std::uint32_t word;
        std::memcpy(&word, &value, 4);
        return word;
      };
      std::printf("{\"range_fixture\":true,\"class\":\"%s\",\"index\":%u,"
                  "\"interpolator\":%s,\"minimum_bits\":%u,\"maximum_bits\":%u,"
                  "\"middle_bits\":%u}\n",
                  cls, i, st.interpolator ? "true" : "false",
                  st.interpolator ? bits(st.interpolator->getMinRange()) : 0u,
                  st.interpolator ? bits(st.interpolator->getMaxRange()) : 0u,
                  st.interpolator ? bits(st.interpolator->getMidRange()) : 0u);
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
  assert(!presonus::dsp::geqSourcePortProvidersReady());
  Core::FormatterRegistry::find("");
  delete Core::InterpolatorFactory::create("linear");
  if (bootstrapped) {
    captureCallbacks = true;
    presonus::dsp::registerGEQSourcePortProviders();
    captureCallbacks = false;
    assert(presonus::dsp::geqSourcePortProvidersReady() && callbackCount >= 1);
    assert(Core::FormatterRegistry::find("gain.1.value"));
  } else
    assert(!Core::FormatterRegistry::find("gain") &&
           !Core::FormatterRegistry::find("time") &&
           !Core::FormatterRegistry::find("ratio"));
  exercise<Comp>("GEQParamList", 33, compC1, compC2, compD1);
  assert(lifecycleCases == 6 && descriptorObservations == 198);
  allReleased();
  mainAllocationCount = observation::count;
  std::atexit(exitObserver);
  if (bootstrapped) {
    const unsigned before = callbackCount;
    captureCallbacks = true;
    observation::watching = observation::Kind::curve;
    auto *comp = Comp::instance();
    observation::watching = observation::Kind::none;
    captureCallbacks = false;
    assert(Comp::instance() == comp && callbackCount == before + 1);
    assert(callbacks[before].function ==
               reinterpret_cast<void (*)(void *)>(compD1) &&
           callbacks[before].object == comp);
    assert(callbacks[0].sequence < callbacks[before].sequence);
    inspect(presonus::dsp::sourceList(*comp), "GEQParamList", 33, false);
    std::printf("{\"callback_records\":[");
    for (unsigned i = 0; i < callbackCount; ++i) {
      auto fd = static_cast<long long>(
          reinterpret_cast<std::intptr_t>(callbacks[i].function) -
          reinterpret_cast<std::intptr_t>(compD1));
      auto od = static_cast<long long>(
          reinterpret_cast<std::intptr_t>(callbacks[i].object) -
          reinterpret_cast<std::intptr_t>(comp));
      std::printf("%s{\"sequence\":%u,\"function_from_comp_d1\":%lld,\"object_"
                  "from_comp_instance\":%lld}",
                  i ? "," : "", callbacks[i].sequence, fd, od);
    }
    std::printf("]}\n");
  }
  std::cout << "{\"passed\":true,\"lifecycle_cases\":" << lifecycleCases
            << ",\"descriptor_observations\":" << descriptorObservations
            << ",\"bootstrapped\":" << (bootstrapped ? "true" : "false")
            << ",\"main_allocations\":" << mainAllocationCount
            << ",\"singleton_callbacks\":" << (bootstrapped ? 1 : 0)
            << ",\"unchanged_callbacks_forwarded\":true}\n";
}
