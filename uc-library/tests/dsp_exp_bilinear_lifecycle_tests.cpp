#ifdef NDEBUG
#undef NDEBUG
#endif
#include "presonus/mixer_dsp/Dsp.hpp"
#include "presonus/mixer_dsp/Interpolators.hpp"
#include <array>
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
extern "C" void
ratioC1(void *) asm("_ZN8Presonus3Dsp20BilinearInterpolatorC1Ev");
extern "C" void
ratioC2(void *) asm("_ZN8Presonus3Dsp20BilinearInterpolatorC2Ev");
extern "C" void
ratioD1(void *) asm("_ZN8Presonus3Dsp20BilinearInterpolatorD1Ev");
extern "C" void
ratioD0(void *) asm("_ZN8Presonus3Dsp20BilinearInterpolatorD0Ev");
extern "C" void skewC1(void *, float, float,
                       float) asm("_ZN8Presonus3Dsp15ExpInterpolatorC1Efff");
extern "C" void skewC2(void *, float, float,
                       float) asm("_ZN8Presonus3Dsp15ExpInterpolatorC2Efff");
extern "C" void skewD1(void *) asm("_ZN8Presonus3Dsp15ExpInterpolatorD1Ev");
extern "C" void skewD0(void *) asm("_ZN8Presonus3Dsp15ExpInterpolatorD0Ev");
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
    (variant == 1 ? ratioC1 : ratioC2)(storage);
  return skew
             ? static_cast<Core::Interpolator *>(
                   static_cast<Presonus::Dsp::ExpInterpolator *>(storage))
             : static_cast<Core::Interpolator *>(
                   static_cast<Presonus::Dsp::BilinearInterpolator *>(storage));
}
std::size_t bytes(bool skew) {
  return skew ? sizeof(Presonus::Dsp::ExpInterpolator)
              : sizeof(Presonus::Dsp::BilinearInterpolator);
}
std::array<float, 9> state(bool exp, void *storage) {
  if (exp) {
    auto s =
        static_cast<Presonus::Dsp::ExpInterpolator *>(storage)->portableState();
    return {s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7], 0};
  }
  const auto &s = static_cast<Presonus::Dsp::BilinearInterpolator *>(storage)
                      ->recoveredState();
  return {
      s.minimum,  s.maximum,   s.midpoint,   s.reserved,   s.normalizedMidpoint,
      s.lowSlope, s.highSlope, s.lowInverse, s.highInverse};
}
__attribute__((noinline)) void virtualDelete(Core::Interpolator *object) {
  delete object;
}
int main(int argc, char **argv) {
  if (argc == 2 && std::strcmp(argv[1], "lifecycle") == 0) {
    const float ratio[][3] = {{0, 1, 1}};
    const float skew[][3] = {
        {0, 1, .25f},   {0, 1, .75f}, {.00002f, .5f, .005f},
        {.05f, 2, .7f}, {-4, 8, 0},   {0, 0, 0},
        {2, 1, 1.5f},   {0, 1, .5f},  {0, 1, 0},
        {0, 1, 1},      {-1, 1, 0},   {-1, 1, -.5f}};
    unsigned cases = 0;
    for (bool useSkew : {false, true})
      for (unsigned variant : {1u, 2u})
        for (unsigned i = 0; i < (useSkew ? 12u : 1u); ++i)
          for (unsigned mode : {0u, 1u, 2u}) {
            observation::capture = true;
            void *storage = ::operator new(bytes(useSkew));
            observation::capture = false;
            auto &allocation = observation::allocations[observation::count - 1];
            const auto &args = useSkew ? skew[i] : ratio[i];
            auto *base = construct(useSkew, variant, args, storage);
            assert(base->getName() == nullptr);
            assert(word(base->getMinRange()) == word(args[0]));
            assert(word(base->getMaxRange()) == word(args[1]));
            auto **vt = *reinterpret_cast<void ***>(storage);
            assert(vt[0] ==
                   reinterpret_cast<void *>(useSkew ? skewD1 : ratioD1));
            assert(vt[1] ==
                   reinterpret_cast<void *>(useSkew ? skewD0 : ratioD0));
            volatile float n = base->normalizedToRange(.5f);
            (void)n;

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
    std::uint32_t words[3]{}, expected[9]{}, mask;
    row >> role >> kind >> variant >> words[0] >> words[1] >> words[2] >> mask;
    for (auto &v : expected)
      row >> v;
    assert(row);
    bool useSkew = kind == "exp";
    float args[3]{floating(words[0]), floating(words[1]), floating(words[2])};
    void *storage = ::operator new(bytes(useSkew));
    Core::Interpolator *base = construct(useSkew, variant, args, storage);
    if (!useSkew || mask == 255) {
      auto s = state(useSkew, storage);
      for (unsigned i = 0; i < (useSkew ? 8u : 9u); ++i)
        assert(word(s[i]) == expected[i]);
    } else {
      assert(mask == 95);
      assert(word(base->getMinRange()) == expected[0]);
      assert(word(base->getMaxRange()) == expected[1]);
      // Do not snapshot inverse members of partial states.
    }
    assert(base->getName() == nullptr);
    std::string op;
    if (row >> op) {
      std::uint32_t value, expectedReturn;
      row >> value >> expectedReturn;
      assert(row);
      assert(op == "N" || !useSkew || mask == 255);
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
