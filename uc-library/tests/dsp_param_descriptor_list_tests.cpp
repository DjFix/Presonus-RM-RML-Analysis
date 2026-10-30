#ifdef NDEBUG
#undef NDEBUG
#endif
#include "presonus/mixer_dsp/ParamDescriptorList.hpp"
#include <cassert>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
using Descriptor = Presonus::Dsp::ParamDescriptor;
using List = Presonus::Dsp::ParamDescriptorList;
using Tag = presonus::dsp::DescriptorSourceTag;
extern "C" void
descriptorD1(Descriptor *) asm("_ZN8Presonus3Dsp15ParamDescriptorD1Ev");
extern "C" void listD2(List *) asm("_ZN8Presonus3Dsp19ParamDescriptorListD2Ev");
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
Allocation records[4096]{};
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
    assert(count < 4096);
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

unsigned formatterDestroyed = 0, interpolatorDestroyed = 0, rangeCalls = 0;
struct ProbeFormatter : Core::Formatter {
  explicit ProbeFormatter(const char *name) : Core::Formatter(name) {}
  ~ProbeFormatter() override { ++formatterDestroyed; }
  void print(Data &d) const override {
    if (d.string && d.size > 0)
      std::snprintf(d.string, d.size, "probe");
  }
};
struct ProbeInterpolator : Core::LinearInterpolator {
  ProbeInterpolator() : Core::LinearInterpolator(0, 1) {}
  ~ProbeInterpolator() override { ++interpolatorDestroyed; }
  void setRange(float a, float b, float c) override {
    ++rangeCalls;
    Core::LinearInterpolator::setRange(a, b, c);
  }
};
Core::Interpolator *createProbe() { return new ProbeInterpolator; }
extern "C" int __real___cxa_atexit(void (*)(void *), void *, void *);
bool watchAtexit = false;
unsigned errorRegistrations = 0;
void *errorObject = nullptr;
extern "C" int __wrap___cxa_atexit(void (*f)(void *), void *p, void *dso) {
  if (watchAtexit) {
    assert(f == reinterpret_cast<void (*)(void *)>(descriptorD1));
    ++errorRegistrations;
    errorObject = p;
  }
  return __real___cxa_atexit(f, p, dso);
}
unsigned exitFmtBefore = 0, exitInterpBefore = 0;
void exitObserver() {
  assert(formatterDestroyed == exitFmtBefore + 1 &&
         interpolatorDestroyed == exitInterpBefore + 1);
  for (unsigned i = 0; i < observation::count; ++i)
    assert(!observation::records[i].alive &&
           observation::records[i].forwarded == 1);
  std::printf(
      "{\"passed\":true,\"actual_error_atexit_cleanup\":true,\"error_"
      "registrations\":%u,\"all_observed_allocations_released\":true}\n",
      errorRegistrations);
}
std::uint32_t word(float value) {
  std::uint32_t r;
  std::memcpy(&r, &value, 4);
  return r;
}
bool ctorCalled = false;
float ctorMin = 0, ctorMax = 0;
extern "C" void
__real__ZN4Core18LinearInterpolatorC1Eff(Core::LinearInterpolator *, float,
                                         float);
extern "C" void
__wrap__ZN4Core18LinearInterpolatorC1Eff(Core::LinearInterpolator *p, float a,
                                         float b) {
  ctorCalled = true;
  ctorMin = a;
  ctorMax = b;
  __real__ZN4Core18LinearInterpolatorC1Eff(p, a, b);
}
void emit(const Descriptor &p, unsigned index) {
  const auto &st = p.sourceState();
  std::printf(
      "{\"fixture\":true,\"case\":%u,\"tag\":%d,\"flags\":%u,\"word10\":%u,"
      "\"word14\":%u,\"word18\":%u,\"text0\":\"%s\",\"text1\":\"%s\",\"text2\":"
      "\"%s\",\"formatter\":%s,\"interpolator\":%s,\"constructor_called\":%s,"
      "\"constructor_min\":%u,\"constructor_max\":%u}\n",
      index, st.tag, st.flags, st.word10, st.word14, st.word18, st.text0.str(),
      st.text1.str(), st.text2.str(), st.formatter ? "true" : "false",
      st.interpolator ? "true" : "false", ctorCalled ? "true" : "false",
      ctorCalled ? word(ctorMin) : 0, ctorCalled ? word(ctorMax) : 0);
}
int main() {
  static ProbeFormatter borrowed("descriptor.test");
  Core::FormatterRegistry::add(&borrowed);
  Core::InterpolatorFactory::add("descriptor.test", createProbe);
  // Initialize source Core registries before scoped allocation observation.
  assert(Core::FormatterRegistry::find("descriptor.test") == &borrowed);
  delete Core::InterpolatorFactory::create("descriptor.test");
  unsigned cases = 0, ownedListFormatters = 0, ownedCurves = 0;
  const char *strings[] = {"one", "two", "three"};
  const char *texts[] = {
      nullptr,
      "",
      "a",
      "1234567890123456789012345678901",
      "12345678901234567890123456789012",
      "123456789012345678901234567890123",
      "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
      "ab\0cd"};
  unsigned beginFmt = formatterDestroyed, beginInterp = interpolatorDestroyed;
  observation::watching = observation::Kind::curve;
  {
    List list(Tag{});
    for (unsigned n = 0; n < 8; ++n)
      for (unsigned kind = 0; kind < 4; ++kind)
        for (int flag : {0, 17}) {
          ctorCalled = false;
          Descriptor *p = nullptr;
          float def = n % 2 ? -.25f : 1.25f;
          if (kind < 2) {
            p = list.addFloat(static_cast<int>(cases) - 10, texts[n],
                              texts[(n + 1) % 8], texts[(n + 2) % 8], -10, 10,
                              def, "descriptor.test",
                              kind ? "absent" : "descriptor.test", .25f, flag);
            ++ownedCurves;
          } else if (kind == 2)
            p = list.addToggle(static_cast<int>(cases) - 10, texts[n],
                               texts[(n + 1) % 8], texts[(n + 2) % 8], def,
                               "descriptor.test", flag);
          else {
            p = list.addList(static_cast<int>(cases) - 10, texts[n],
                             texts[(n + 1) % 8], texts[(n + 2) % 8], strings, 3,
                             def, flag);
            ++ownedListFormatters;
            ++ownedCurves;
          }
          assert(list.getAt(static_cast<int>(cases)) == p &&
                 list.sourceCount() == static_cast<int>(cases) + 1);
          const auto &st = p->sourceState();
          assert(st.tag == static_cast<int>(cases) - 10 &&
                 st.word14 == word(def) && st.word18 == 32);
          assert(st.flags == (static_cast<unsigned>(flag) |
                              (kind == 3 ? 0x10024u : 0x20u)));
          assert(st.word10 == (kind < 2 ? 0u : kind == 2 ? 2u : 3u));
          const Core::CStringBuffer<32> *copies[] = {&st.text0, &st.text1,
                                                     &st.text2};
          for (unsigned i = 0; i < 3; ++i) {
            const char *original = texts[(n + i) % 8];
            if (!original)
              original = "";
            unsigned length = std::strlen(original);
            if (length > 31)
              length = 31;
            assert(std::strlen(copies[i]->str()) == length &&
                   std::strncmp(copies[i]->str(), original, length) == 0);
          }
          if (kind == 3) {
            char out[16]{};
            Core::Formatter::Data data{nullptr, out, 16, 1.f, nullptr};
            st.formatter->print(data);
            assert(std::strcmp(out, "two") == 0);
            assert(st.interpolator->normalizedToRange(.5f) == 1.f);
          } else {
            assert(st.formatter == &borrowed);
            if (kind < 2)
              assert(st.interpolator->normalizedToRange(.5f) == 0.f);
            else
              assert(!st.interpolator);
          }
          emit(*p, cases);
          ++cases;
        }
    assert(cases == 64);
    const float minima[] = {0.f, -0.f, 10.f, -1.e20f};
    const float maxima[] = {0.f, 1.f, -10.f, 1.e20f};
    const std::uint32_t defaults[] = {0, 0x80000000u, 1, 0x7f7fffffu};
    for (unsigned n = 0; n < 4; ++n)
      for (unsigned missing = 0; missing < 2; ++missing) {
        ctorCalled = false;
        float def;
        std::memcpy(&def, &defaults[n], 4);
        auto *p = list.addFloat(static_cast<int>(cases) - 10, "extra", "",
                                nullptr, minima[n], maxima[n], def,
                                missing ? "absent" : "descriptor.test",
                                "absent", .5f, n % 2 ? (-2147483647 - 1) : 0);
        assert(list.getAt(static_cast<int>(cases)) == p &&
               p->sourceState().word14 == defaults[n]);
        assert(bool(p->sourceState().formatter) == !missing);
        emit(*p, cases++);
      }
    for (int count : {0, 1, 2, 3, 17, -1, 16777217, 2147483647}) {
      ctorCalled = false;
      auto *p = list.addList(static_cast<int>(cases) - 10, "count", "", nullptr,
                             strings, count, -0.f, 0);
      assert(list.getAt(static_cast<int>(cases)) == p &&
             p->sourceState().word10 == static_cast<std::uint32_t>(count));
      // Count metadata/construction only; no indexing borrowed strings when
      // count exceeds their actual extent or is nonpositive.
      emit(*p, cases++);
    }
    assert(cases == 80);
  }
  observation::watching = observation::Kind::none;
  assert(formatterDestroyed == beginFmt &&
         interpolatorDestroyed == beginInterp + 16 && rangeCalls == 16);
  for (unsigned i = 0; i < observation::count; ++i)
    assert(!observation::records[i].alive &&
           observation::records[i].forwarded == 1);
  // D1 directly: borrowed formatter survives, owned interpolator really
  // deleted.
  for (unsigned owned = 0; owned < 2; ++owned)
    for (unsigned children = 0; children < 4; ++children) {
      observation::watching = observation::Kind::curve;
      void *storage = ::operator new(sizeof(Descriptor));
      auto *p = new (storage) Descriptor(Tag{});
      auto &st = p->sourceState();
      st.formatter = children & 1
                         ? (owned ? new ProbeFormatter("direct") : &borrowed)
                         : nullptr;
      st.interpolator = children & 2 ? new ProbeInterpolator : nullptr;
      st.flags = owned ? 0x10000u : 0;
      unsigned before = formatterDestroyed;
      descriptorD1(p);
      assert(formatterDestroyed == before + ((children & 1) ? owned : 0));
      assert(observation::find(storage));
      ::operator delete(storage);
      observation::watching = observation::Kind::none;
    }
  // Original D2 identity is called separately; real nested allocations release.
  observation::watching = observation::Kind::curve;
  void *listStorage = ::operator new(sizeof(List));
  auto *explicitList = new (listStorage) List(Tag{});
  explicitList->addList(1, "a", "b", "c", strings, 3, 1, 0);
  listD2(explicitList);
  assert(observation::find(listStorage));
  ::operator delete(listStorage);
  observation::watching = observation::Kind::none;
  // Real process-exit registration and actual forwarded destructor execution.
  std::atexit(exitObserver);
  watchAtexit = true;
  Descriptor *error = List::getError();
  watchAtexit = false;
  assert(errorRegistrations == 1 && errorObject == error &&
         List::getError() == error);
  assert(error->sourceState().flags == 32 && error->sourceState().word18 == 32);
  {
    List empty(Tag{});
    assert(empty.getAt(-1) == error && empty.getAt(0) == error &&
           empty.getAt(2147483647) == error);
  }
  exitFmtBefore = formatterDestroyed;
  exitInterpBefore = interpolatorDestroyed;
  observation::watching = observation::Kind::curve;
  error->sourceState().formatter = new ProbeFormatter("exit");
  error->sourceState().interpolator = new ProbeInterpolator;
  error->sourceState().flags |= 0x10000u;
  observation::watching = observation::Kind::none;
  std::cout << "{\"passed\":true,\"ordinary_cases\":" << cases
            << ",\"real_core_factory_range_callbacks\":" << rangeCalls
            << ",\"direct_descriptor_lifecycles\":8,\"direct_list_d2_"
               "lifecycles\":1,\"original_error_target_registered\":true}\n";
}
