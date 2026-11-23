#include "presonus/mixer/FXComponent.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <stdexcept>

using Receiver = Presonus::Mixer::FXComponent;

namespace {
void invokeVirtual(Receiver &receiver) { receiver.tap(); }

struct Probe : Receiver {
  using Receiver::Receiver;
  void tap() override { ++calls; }
  unsigned calls = 0;
};

void checkRoutes(Probe &probe) {
  // Force a qualified direct call and verify the other site dispatches
  // through the dynamic type with a distinct, observable test override.
  probe.Receiver::tap();
  if (probe.calls != 0)
    throw std::runtime_error("qualified call selected test override");
  invokeVirtual(probe);
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

bool runCase(bool viaTable, unsigned seed) {
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
  if (viaTable)
    invokeVirtual(receiver);
  else
    receiver.Receiver::tap();
  return receiverBytes(receiver) == snapshot && app.calls == 0 &&
         state.dirty == bool(seed & 1) &&
         state.recalledTypePending == bool(seed & 2) && !state.load &&
         state.displayedTypeParameter == &displayed &&
         state.interpolation == &interpolation &&
         interpolation.parameters == decltype(interpolation.parameters){} &&
         interpolation.deferred.count() == deferredCount &&
         current.getValue() == seed / 4.f &&
         recalled.getValue() == (3 - seed) / 4.f &&
         displayed.getValue() == 0.5f && parameters.countParameters() == 0;
}

} // namespace

int main() {
  unsigned route, seed;
  while (std::cin >> route >> seed) {
    if (route > 1 || seed > 3)
      return 2;
    std::cout << runCase(route != 0, seed) << '\n';
  }
  return std::cin.eof() ? 0 : 2;
}
