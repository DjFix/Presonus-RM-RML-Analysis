#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/panel/FrontPanelComponent.hpp"

#include <array>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string_view>

namespace {
using presonus::frontpanel_port::Action;
class UnexpectedPanelServices final
    : public presonus::frontpanel_port::Dependencies {
public:
  void perform(Action, int, int) override { std::abort(); }
  bool timerLongEnough() const override { std::abort(); }
  bool fadersLocked() const override { std::abort(); }
  const char *activePageName() const override { std::abort(); }
  void paste(void *, const void *, const char *) override { std::abort(); }
};

template <typename T> auto objectBytes(const T &object) {
  std::array<unsigned char, sizeof(T)> bytes;
  std::memcpy(bytes.data(), &object, sizeof(T));
  return bytes;
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const std::string_view name = argv[1];
  if (name != "idle" && name != "active")
    return 2;
  const bool active = name == "active";
  Core::Portable::Component settings;
  presonus::frontpanel_port::State initial(settings);
  UnexpectedPanelServices services;
  Presonus::Panel::FrontPanelComponent panel(initial, services);
  presonus::mixer::ChannelState channelState;
  Presonus::Mixer::ChannelComponent channel(
      Presonus::Mixer::ChannelComponent::SourcePortConstruction{},
      channelState);
  auto &front = panel.portableFrontState();
  front.panelMode = active ? 7 : 0;
  front.fatChannelDirty = active;
  front.controlsBlocked = active;
  front.heldButton = active ? 4 : -1;
  channelState.active = active;
  channelState.gain = active ? 0.75f : 0.0f;
  channelState.updates.fill(active ? 0x5aa55aa5u : 0u);

  const auto frontBefore = objectBytes(front);
  const auto panelBefore = objectBytes(panel);
  const auto channelBefore = objectBytes(channel);
  const auto channelStateBefore = objectBytes(channelState);
  const auto settingsBefore = objectBytes(settings);
  auto hook = &Presonus::Panel::FrontPanelComponent::doFatMeterUpdate;
  (panel.*hook)(channel);
  const bool unchanged = frontBefore == objectBytes(front) &&
                         panelBefore == objectBytes(panel) &&
                         channelBefore == objectBytes(channel) &&
                         channelStateBefore == objectBytes(channelState) &&
                         settingsBefore == objectBytes(settings);
  std::cout << (unchanged ? "unchanged" : "changed") << '\n';
  return unchanged ? 0 : 1;
}
