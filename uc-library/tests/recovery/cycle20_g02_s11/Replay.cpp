#define RECOVERY_TASK 11
#include "presonus/MeterBallistics.hpp"

#if RECOVERY_TASK == 13 || RECOVERY_TASK == 14 || RECOVERY_TASK == 15 ||       \
    RECOVERY_TASK == 20
#include "core/portable/coreparams.h"
#include "presonus/MeterMaid.hpp"
#endif

#include <bit>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string>

namespace presonus::meter {
struct MeterStateAccess {
  static auto &state(Presonus::MeterBallistics &meter) { return meter.state_; }
  static auto &table(Presonus::MeterBallistics &meter) {
    return meter.decayTable_;
  }
#if RECOVERY_TASK == 13
  static bool empty(Presonus::MeterMaid &maid) {
    return !maid.meter_ && !maid.peak_ && maid.auxiliary_[0] == 0 &&
           maid.auxiliary_[1] == 0;
  }
#endif
};
} // namespace presonus::meter

namespace {
using Presonus::MeterBallistics;
using presonus::meter::MeterStateAccess;

std::uint32_t bits(float value) { return std::bit_cast<std::uint32_t>(value); }
float binary32(std::uint32_t word) { return std::bit_cast<float>(word); }

#if RECOVERY_TASK == 8 || RECOVERY_TASK == 13
void inspect(MeterBallistics &meter) {
  const auto &s = MeterStateAccess::state(meter);
  auto *table = MeterStateAccess::table(meter);
  static const auto *shared = table;
  if (!table || shared != table)
    std::abort();
  std::cout << s.mode << ' ' << bits(s.scale) << ' ' << bits(s.decayRate) << ' '
            << s.active << ' ' << bits(s.amplitude) << ' ' << bits(s.peakHold);
  for (auto word : s.auxiliary)
    std::cout << ' ' << word;
  for (const auto &entry : table->entries())
    std::cout << ' ' << bits(entry.amplitude) << ' '
              << bits(entry.normalizedInterval);
}
#endif

#if RECOVERY_TASK == 19 || RECOVERY_TASK == 20
void *expectedDelete = nullptr;
unsigned releaseCount = 0;
[[gnu::noinline]] void deleteMeter(MeterBallistics *meter) { delete meter; }

template <typename T> bool lifecycle(bool deleting, unsigned seed) {
  if (deleting) {
    T *meter = new T;
    MeterStateAccess::state(*meter).auxiliary.fill(seed);
    expectedDelete = meter;
    releaseCount = 0;
    deleteMeter(meter);
    const bool correct = expectedDelete == nullptr && releaseCount == 1;
    expectedDelete = nullptr;
    return correct;
  }
  alignas(T) unsigned char storage[sizeof(T)];
  T *meter = new (storage) T;
  MeterStateAccess::state(*meter).auxiliary.fill(seed);
  releaseCount = 0;
  meter->T::~T();
  return releaseCount == 0;
}
#endif
} // namespace

#if RECOVERY_TASK == 19 || RECOVERY_TASK == 20
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *address) {
  if (address == expectedDelete) {
    if (!address || releaseCount)
      std::abort();
    ++releaseCount;
    expectedDelete = nullptr;
  }
  __real__ZdlPv(address);
}
#endif

int main() {
#if RECOVERY_TASK == 8 || RECOVERY_TASK == 13
  int warm;
  while (std::cin >> warm) {
#if RECOVERY_TASK == 13
    Presonus::MeterMaid meter;
    if (!MeterStateAccess::empty(meter))
      return 2;
    inspect(meter);
    std::cout << " 0 0 0 0";
#else
    MeterBallistics meter;
    inspect(meter);
#endif
    std::cout << '\n';
  }
#elif RECOVERY_TASK == 9
  std::uint32_t peak;
  while (std::cin >> peak) {
    MeterBallistics meter;
    MeterStateAccess::state(meter).peakHold = binary32(peak);
    std::cout << bits(meter.getPeakHold()) << '\n';
  }
#elif RECOVERY_TASK == 10
  std::uint32_t peak;
  while (std::cin >> peak) {
    MeterBallistics meter;
    auto &s = MeterStateAccess::state(meter);
    s.amplitude = -0.5f;
    s.peakHold = binary32(peak);
    s.auxiliary.fill(0xa5a5a5a5);
    auto *table = MeterStateAccess::table(meter);
    const float rate = s.decayRate;
    meter.reset();
    if (s.decayRate != rate || table != MeterStateAccess::table(meter) ||
        !s.active || s.mode || s.scale != 1.f)
      return 2;
    std::cout << bits(s.amplitude) << ' ' << bits(s.peakHold);
    for (auto word : s.auxiliary)
      std::cout << ' ' << word;
    std::cout << '\n';
  }
#elif RECOVERY_TASK == 11 || RECOVERY_TASK == 12
  bool bound;
  std::uint32_t level, rate;
  while (std::cin >> bound >> level >> rate) {
    MeterBallistics meter;
    auto &s = MeterStateAccess::state(meter);
    s.amplitude = s.peakHold = binary32(level);
    s.decayRate = binary32(rate);
    if (!bound)
      MeterStateAccess::table(meter) = nullptr;
#if RECOVERY_TASK == 11
    const float result = meter.getDecayDelta();
#else
    const float result = meter.getPeakDecayDelta();
#endif
    if (s.amplitude != binary32(level) || s.peakHold != binary32(level) ||
        s.decayRate != binary32(rate))
      return 2;
    std::cout << bits(result) << '\n';
  }
#elif RECOVERY_TASK == 14 || RECOVERY_TASK == 15
  bool bound;
  std::uint32_t input;
  while (std::cin >> bound >> input) {
    using namespace Core::Portable;
    ParamInfo info{};
    info.type = ParamInfo::kFloat;
    info.minValue = 0.f;
    info.maxValue = 1.f;
    info.defaultValue = 0.75f;
    NumericParam primary(info), other(info);
    Presonus::MeterMaid meter;
#if RECOVERY_TASK == 14
    meter.bindParameters(bound ? &primary : nullptr, &other);
    meter.setMeter(binary32(input));
#else
    meter.bindParameters(&other, bound ? &primary : nullptr);
    meter.setPeak(binary32(input));
#endif
    const float expected = bound ? binary32(input) : info.defaultValue;
    if (primary.getValue() != expected || other.getValue() != info.defaultValue)
      return 2;
    std::cout << (primary.getValue() != info.defaultValue) << '\n';
  }
#else
  unsigned seed;
  std::string variant;
  while (std::cin >> seed >> variant) {
    if (variant != "D0" && variant != "D1")
      return 2;
#if RECOVERY_TASK == 19
    if (!lifecycle<MeterBallistics>(variant == "D0", seed))
      return 3;
#else
    if (!lifecycle<Presonus::MeterMaid>(variant == "D0", seed))
      return 3;
#endif
    std::cout << (variant == "D0") << '\n';
  }
#endif
}
