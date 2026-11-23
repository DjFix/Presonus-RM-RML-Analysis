#include "presonus/mixer/FXComponent.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <stdexcept>

using Receiver = Presonus::Mixer::FXComponent;

namespace {
int invokeVirtual(Receiver &receiver, int selector) {
  return receiver.mapIDs(selector);
}

struct Probe : Receiver {
  using Receiver::Receiver;
  int mapIDs(int selector) override {
    ++calls;
    return selector;
  }
  unsigned calls = 0;
};

void checkRoutes(Probe &probe) {
  // Force a qualified direct call and verify the other site dispatches
  // through the dynamic type with a distinct, observable test override.
  if (probe.Receiver::mapIDs(42) != -1)
    throw std::runtime_error("unexpected qualified result");
  if (probe.calls != 0)
    throw std::runtime_error("qualified call selected test override");
  if (invokeVirtual(probe, 42) != 42)
    throw std::runtime_error("virtual route changed selector");
  if (probe.calls != 1)
    throw std::runtime_error("virtual call bypassed test override");
}

using Snapshot = std::array<unsigned char, sizeof(Receiver)>;

Snapshot receiverBytes(const Receiver &receiver) {
  Snapshot bytes;
  std::memcpy(bytes.data(), &receiver, bytes.size());
  return bytes;
}

struct Boundary final : presonus::mixer_fx::AppBoundary {
  void setControllerDirty() override { ++calls; }
  std::uint32_t getTypeNumber() override {
    ++calls;
    return 0;
  }
  void updateTypeName() override { ++calls; }
  void handleTypeChange(bool) override { ++calls; }
  unsigned calls = 0;
};

std::uint32_t runCase(bool viaTable, int selector) {
  const unsigned seed = static_cast<unsigned>(selector) & 3u;
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  info.minValue = 0.f;
  info.maxValue = 1.f;
  Core::Portable::Component parameters;
  Core::Portable::NumericParam current{info}, recalled{info}, displayed{info};
  current.setValue(seed / 4.f, false);
  recalled.setValue((3 - seed) / 4.f, false);
  displayed.setValue(0.5f, false);
  Boundary app;
  presonus::mixer_fx::InterpolatorState interpolation;
  presonus::mixer_fx::State state{parameters, current, recalled, app};
  state.displayedTypeParameter = &displayed;
  state.interpolation = &interpolation;
  state.dirty = seed & 1;
  state.recalledTypePending = seed & 2;
  Receiver receiver{state};
  Probe probe{state};
  checkRoutes(probe);
  const auto snapshot = receiverBytes(receiver);
  const auto deferredCount = interpolation.deferred.count();
  const auto result = viaTable ? invokeVirtual(receiver, selector)
                               : receiver.Receiver::mapIDs(selector);
  const bool unchanged =
      receiverBytes(receiver) == snapshot && app.calls == 0 &&
      state.dirty == bool(seed & 1) &&
      state.recalledTypePending == bool(seed & 2) && !state.load &&
      state.displayedTypeParameter == &displayed &&
      state.interpolation == &interpolation &&
      interpolation.parameters == decltype(interpolation.parameters){} &&
      interpolation.deferred.count() == deferredCount &&
      current.getValue() == seed / 4.f &&
      recalled.getValue() == (3 - seed) / 4.f && displayed.getValue() == 0.5f &&
      parameters.countParameters() == 0;
  if (!unchanged)
    throw std::runtime_error("FX state changed");
  return static_cast<std::uint32_t>(result);
}

} // namespace

int main() {
  unsigned route;
  int selector;
  while (std::cin >> route >> selector) {
    if (route > 1)
      return 2;
    std::cout << runCase(route != 0, selector) << '\n';
  }
  return std::cin.eof() ? 0 : 2;
}
