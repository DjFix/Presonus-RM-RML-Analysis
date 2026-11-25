#include "presonus/surface/DAWMixerHandler.hpp"
#include <cstdlib>
#include <iostream>

namespace {
struct Dependencies final : presonus::surface::DAWMixerDependencies {
  Presonus::DAWChannel *focusChannel() override { std::abort(); }
  Presonus::DAWChannel *mainChannel() override { std::abort(); }
  int selectedMix() const override { std::abort(); }
  bool showStripMeters() const override { std::abort(); }
  Core::Portable::Component *component(Presonus::DAWChannel *) const override {
    std::abort();
  }
  Presonus::DAWDeviceFolder *folder(Presonus::DAWChannel *,
                                    bool) const override {
    std::abort();
  }
  int usedCount(Presonus::DAWDeviceFolder *) const override { std::abort(); }
  Core::Portable::Component *slot(Presonus::DAWDeviceFolder *,
                                  int) const override {
    std::abort();
  }
  const char *channelType(Presonus::DAWChannel *) const override {
    std::abort();
  }
  void connect(const char *, Core::Portable::Parameter *, const char *,
               bool) override {
    std::abort();
  }
  void assignChannels() override { std::abort(); }
  void assignControlLinkTargets() override { std::abort(); }
  void assignSelectedChannelTargets() override { std::abort(); }
  void assignFlexStrip() override { std::abort(); }
};
} // namespace

int main() {
  Dependencies dependencies;
  presonus::surface::DAWMixerState leftState, rightState;
  leftState.shift = 1;
  rightState.clientPresent = true;
  Presonus::Surface::DAWMixerHandler left(dependencies, leftState);
  Presonus::Surface::DAWMixerHandler right(dependencies, rightState);
  Core::Portable::ParamInfo info{};
  Core::Portable::NumericParam parameter(info);
  parameter.setValueFast(0.75f);
  std::cout << left.handleMappingRadioGroup(nullptr) << '\n'
            << left.handleMappingRadioGroup(&parameter) << '\n'
            << right.handleMappingRadioGroup(nullptr) << '\n'
            << right.handleMappingRadioGroup(&parameter) << '\n';
  return parameter.getValue() == 0.75f && leftState.shift == 1 &&
                 !leftState.clientPresent && rightState.clientPresent &&
                 rightState.shift == 0
             ? 0
             : 1;
}
