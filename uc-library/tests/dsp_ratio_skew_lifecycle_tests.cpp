#ifdef NDEBUG
#undef NDEBUG
#endif
#include "presonus/mixer_dsp/Interpolators.hpp"
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <new>
#include <sstream>
#include <string>
extern "C" void ratioC1(void *, float,
                        float) asm("_ZN8Presonus3Dsp17RatioInterpolatorC1Eff");
extern "C" void ratioC2(void *, float,
                        float) asm("_ZN8Presonus3Dsp17RatioInterpolatorC2Eff");
extern "C" void ratioD1(void *) asm("_ZN8Presonus3Dsp17RatioInterpolatorD1Ev");
extern "C" void ratioD0(void *) asm("_ZN8Presonus3Dsp17RatioInterpolatorD0Ev");
extern "C" void skewC1(void *, float, float,
                       float) asm("_ZN8Presonus3Dsp16SkewInterpolatorC1Efff");
extern "C" void skewC2(void *, float, float,
                       float) asm("_ZN8Presonus3Dsp16SkewInterpolatorC2Efff");
extern "C" void skewD1(void *) asm("_ZN8Presonus3Dsp16SkewInterpolatorD1Ev");
extern "C" void skewD0(void *) asm("_ZN8Presonus3Dsp16SkewInterpolatorD0Ev");
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
Allocation allocations[512]{};
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
    assert(observation::count < 512);
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
std::uint32_t word(float value) {
  std::uint32_t result;
  std::memcpy(&result, &value, 4);
  return result;
}
float floating(std::uint32_t value) {
  float result;
  std::memcpy(&result, &value, 4);
  return result;
}
Core::Interpolator *construct(bool skew, unsigned variant,
                              const float (&args)[3], void *storage) {
  if (skew)
    (variant == 1 ? skewC1 : skewC2)(storage, args[0], args[1], args[2]);
  else
    (variant == 1 ? ratioC1 : ratioC2)(storage, args[0], args[1]);
  return skew ? static_cast<Core::Interpolator *>(
                    static_cast<Presonus::Dsp::SkewInterpolator *>(storage))
              : static_cast<Core::Interpolator *>(
                    static_cast<Presonus::Dsp::RatioInterpolator *>(storage));
}
std::size_t bytes(bool skew) {
  return skew ? sizeof(Presonus::Dsp::SkewInterpolator)
              : sizeof(Presonus::Dsp::RatioInterpolator);
}
presonus::dsp::InterpolationState state(bool skew, void *storage) {
  return skew ? static_cast<Presonus::Dsp::SkewInterpolator *>(storage)
                    ->portableState()
              : static_cast<Presonus::Dsp::RatioInterpolator *>(storage)
                    ->portableState();
}
__attribute__((noinline)) void virtualDelete(Core::Interpolator *object) {
  delete object;
}
int main(int argc, char **argv) {
  if (argc == 2 && std::strcmp(argv[1], "lifecycle") == 0) {
    const float ratio[][3] = {
        {1, 20, 0},  {1, 100, 0}, {2, 100, 0},        {.5f, 4, 0},
        {.1f, 1, 0}, {0, 1, 0},   {-1, 2, 0},         {2, 1, 0},
        {1, 1, 0},   {0, 0, 0},   {1e-12f, 1e12f, 0}, {-1e-12f, -1e12f, 0}};
    const float skew[][3] = {{0, 1, .5f},    {20, 100, 40}, {-84, 0, -21},
                             {.05f, 2, .7f}, {0, 0, 0},     {1, 1, 1},
                             {2, 1, 1.5f},   {0, 1, -1},    {-1, 1, 0},
                             {0, 1, 0},      {0, 1, 1},     {1e-12f, 1e12f, 2}};
    unsigned cases = 0;
    for (bool useSkew : {false, true})
      for (unsigned variant : {1u, 2u})
        for (unsigned i = 0; i < 12; ++i)
          for (unsigned mode : {0u, 1u, 2u}) {
            observation::capture = true;
            void *storage = ::operator new(bytes(useSkew));
            observation::capture = false;
            auto &allocation = observation::allocations[observation::count - 1];
            const auto &args = useSkew ? skew[i] : ratio[i];
            auto *base = construct(useSkew, variant, args, storage);
            assert(base->getName() == nullptr);
            auto s = state(useSkew, storage);
            assert(word(s[0]) == word(args[0]) && word(s[1]) == word(args[1]));
            assert(word(s[2]) == word(useSkew ? args[2] : -1.f));
            if (useSkew)
              assert(s[3] == 0 && s[4] == 1 && s[5] == 1 && s[6] == 1);
            auto **vt = *reinterpret_cast<void ***>(storage);
            assert(vt[0] ==
                   reinterpret_cast<void *>(useSkew ? skewD1 : ratioD1));
            assert(vt[1] ==
                   reinterpret_cast<void *>(useSkew ? skewD0 : ratioD0));
            volatile float n = base->normalizedToRange(.5f),
                           r = base->rangeToNormalized(1.f);
            (void)n;
            (void)r;
            if (mode == 0) {
              (useSkew ? skewD1 : ratioD1)(storage);
              assert(allocation.alive && allocation.forwarded == 0);
              ::operator delete(storage);
            } else if (mode == 1)
              (useSkew ? skewD0 : ratioD0)(storage);
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
              << ",\"real_allocations\":" << observation::count
              << ",\"actual_sized_deletes\":" << sized
              << ",\"actual_unsized_deletes\":" << unsized
              << ",\"all_released\":true}" << std::endl;
    return 0;
  }
  assert(argc == 3 && std::strcmp(argv[1], "fixtures") == 0);
  std::ifstream input(argv[2]);
  assert(input);
  std::string line;
  unsigned count = 0, virtualCount = 0;
  while (std::getline(input, line)) {
    std::istringstream row(line);
    std::string role, kind;
    unsigned variant;
    std::uint32_t words[3]{}, expected[8]{};
    row >> role >> kind >> variant >> words[0] >> words[1] >> words[2];
    for (auto &v : expected)
      row >> v;
    assert(row);
    bool useSkew = kind == "skew";
    float args[3]{floating(words[0]), floating(words[1]), floating(words[2])};
    void *storage = ::operator new(bytes(useSkew));
    Core::Interpolator *base = construct(useSkew, variant, args, storage);
    auto s = state(useSkew, storage);
    for (unsigned i = 0; i < 8; ++i)
      assert(word(s[i]) == expected[i]);
    assert(base->getName() == nullptr);
    std::string op;
    if (row >> op) {
      std::uint32_t value, expectedReturn;
      row >> value >> expectedReturn;
      assert(row);
      float result = op == "N" ? base->normalizedToRange(floating(value))
                               : base->rangeToNormalized(floating(value));
      if (word(result) != expectedReturn) {
        std::cerr << kind << ' ' << op << ' ' << value << ' ' << word(result)
                  << ' ' << expectedReturn << std::endl;
        return 3;
      }
      ++virtualCount;
    }
    virtualDelete(base);
    ++count;
  }
  std::cout << "{\"passed\":true,\"fixture_rows\":" << count
            << ",\"virtual_observations\":" << virtualCount << "}" << std::endl;
}
