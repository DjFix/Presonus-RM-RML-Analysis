#define RECOVERY_TASK 16
#include "presonus/MeterMaid.hpp"

#include "core/portable/coreparams.h"

#include <bit>
#include <cstdint>
#include <iostream>

namespace {
using namespace Core::Portable;

class Probe final : public NumericParam {
public:
  using NumericParam::NumericParam;

  ParamValue getValue() const override {
    ++reads;
    return NumericParam::getValue();
  }
  void setValue(ParamValue value, bool edit) override {
    ++writes;
    last = value;
    lastEdit = edit;
    NumericParam::setValue(value, edit);
  }
  ParamValue peek() const { return NumericParam::getValue(); }

  mutable int reads = 0;
  int writes = 0;
  float last = 0.f;
  bool lastEdit = true;
};

ParamInfo info(float initial) {
  ParamInfo result{};
  result.type = ParamInfo::kFloat;
  result.minValue = -1.f;
  result.maxValue = 1.f;
  result.defaultValue = initial;
  return result;
}
} // namespace

int main() {
  bool bound;
  std::uint32_t value;
  while (std::cin >> bound >> value) {
    constexpr float initial = 0.25f;
#if RECOVERY_TASK == 18
    const auto targetInfo = info(std::bit_cast<float>(value));
#else
    const auto targetInfo = info(initial);
#endif
    const auto peerInfo = info(initial);
    Probe target(targetInfo), other(peerInfo), meter(peerInfo), peak(peerInfo);
    Presonus::MeterMaid maid;
    maid.bindParameters(&meter, &peak);
#if RECOVERY_TASK == 16
    maid.bindIndicatorParameters(bound ? &target : nullptr, &other);
    maid.setSignal(value != 0);
#elif RECOVERY_TASK == 17
    maid.bindIndicatorParameters(&other, bound ? &target : nullptr);
    maid.setClipped(value != 0);
#else
    maid.bindIndicatorParameters(&other, bound ? &target : nullptr);
    const auto &constant = maid;
    const bool result = constant.isClipped();
    if (target.reads != static_cast<int>(bound) || target.writes != 0 ||
        std::bit_cast<std::uint32_t>(target.peek()) != value)
      return 2;
    std::cout << result << '\n';
#endif
#if RECOVERY_TASK != 18
    const float signal = static_cast<float>(value != 0);
    if (target.reads != 0 || target.writes != static_cast<int>(bound) ||
        target.peek() != (bound ? signal : initial) ||
        (bound && (target.lastEdit || target.last != signal)))
      return 3;
    std::cout << target.writes << '\n';
#endif
    for (auto *peer : {&other, &meter, &peak}) {
      if (peer->reads || peer->writes || peer->peek() != initial)
        return 4;
    }
  }
}
