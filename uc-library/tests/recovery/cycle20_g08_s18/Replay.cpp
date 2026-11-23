#include "presonus/panel/RackPanelComponent.hpp"

#include <iostream>
#include <tuple>
#include <type_traits>

using Presonus::Panel::RackPanelComponent;

namespace {
class Dependencies final : public presonus::rackpanel_port::Dependencies {
public:
  Presonus::Panel::ControlGroup &group(int) override {
    ++calls;
    return controls;
  }
  Core::Portable::Component &monitorParameters() override {
    ++calls;
    return parameters;
  }
  const std::vector<presonus::rackpanel_port::Channel> &
  channels() const override {
    ++calls;
    return channels_;
  }
  int numClients() const override {
    ++calls;
    return 0;
  }
  void removeDelegate(RackPanelComponent &) override { ++calls; }

  mutable unsigned calls = 0;

private:
  presonus::panel_binding::ControlGroupState controlStorage;
  Presonus::Panel::ControlGroup controls{controlStorage};
  Core::Portable::Component parameters{"rack test"};
  std::vector<presonus::rackpanel_port::Channel> channels_;
};

auto timerValues(const Presonus::DelayTimer &timer) {
  const auto state = presonus::timing::DelayTimerAccess::get(timer);
  return std::make_tuple(state.start, state.duration, state.elapsed,
                         state.reciprocal, state.executing);
}

void dispatch(RackPanelComponent &rack) { rack.dismissAlert(); }
} // namespace

int main() {
  static_assert(std::is_same_v<decltype(&RackPanelComponent::dismissAlert),
                               void (RackPanelComponent::*)()>);
  using namespace Core::Portable;
  const ParamInfo parameter =
      PARAM_FLOAT(8, "display", 0, 1, 0, 1, "", nullptr, 0, 0);
  unsigned virtualDispatch, seed;
  while (std::cin >> virtualDispatch >> seed) {
    Dependencies deps;
    Presonus::Panel::PanelTask task;
    RackPanelComponent rack(deps);
    rack.addParameters(&parameter, 1);
    rack.getParameterByTag(8)->setValue(0.5f, false);
    rack.portableState().active = seed % 2 != 0;
    rack.panelStatus = static_cast<int>(seed % 4);
    rack.burnInHeldCount = seed;
    rack.permissionFlags = seed % 9;
    rack.savedMonitorValue = static_cast<float>(seed % 2);
    rack.tasks.add(&task);
    presonus::timing::DelayTimerAccess::set(rack.statusTimer,
                                            {seed, 1000, 7, 0.001f, true});
    auto observe = [&] {
      return std::make_tuple(
          rack.portableState().active,
          rack.portableState().embeddedHandlerState, rack.panelStatus,
          rack.burnInHeldCount, rack.permissionFlags, rack.savedMonitorValue,
          rack.tasks.count(), rack.tasks.at(0), rack.meterLEDs.size(),
          rack.clipLEDs.size(), rack.phantomLEDs.size(), rack.countParameters(),
          rack.getParameterByTag(8)->getValue(), timerValues(rack.statusTimer),
          deps.calls);
    };
    const auto before = observe();
    if (virtualDispatch)
      dispatch(rack);
    else
      rack.RackPanelComponent::dismissAlert();
    std::cout << (before == observe()) << '\n';
  }
  return std::cin.eof() ? 0 : 3;
}
