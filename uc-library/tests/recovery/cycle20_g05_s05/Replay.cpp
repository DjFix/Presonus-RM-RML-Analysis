#include "presonus/panel/Fat24FrontPanelComponent.hpp"
#include "presonus/panel/PresetComponent.hpp"
#include "presonus/panel/StormFrontPanelComponent.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <type_traits>

namespace {
using namespace Presonus::Panel;
using Presonus::Mixer::ChannelComponent;
using presonus::stormpanel_port::Handle;

struct PresetServices final : presonus::panel::PresetApplicationServices {
  int selectedSlot(const PresetComponent &) const override { fail(); }
  bool slotEmpty(const PresetComponent &, unsigned) const override { fail(); }
  void slotFileName(Core::CString256 &, const PresetComponent &,
                    unsigned) const override {
    fail();
  }
  const char *presetFolder(const PresetComponent &) const override {
    ++teardownCalls;
    return "offline";
  }
  void ensureNameManager() const override { ++teardownCalls; }
  PresetNameCache *lookupCache(const char *) const override {
    ++teardownCalls;
    return nullptr;
  }
  bool hasSelectedSlotParameter(const PresetComponent &) const override {
    fail();
  }
  void presetInfo(Core::CString64 &, Core::CString32 &, int,
                  const char *) const override {
    fail();
  }
  const char *emptyNameMarker() const override { fail(); }
  void updateSelection(PresetComponent &) override { fail(); }
  int recallAttributes(PresetComponent &, Core::Portable::Attributes &,
                       bool) override {
    fail();
  }
  void notifyDelegate(PresetComponent::Delegate *, const PresetComponent &, int,
                      bool) const override {
    fail();
  }

  mutable int teardownCalls = 0;

private:
  [[noreturn]] static void fail() {
    throw std::logic_error("Unexpected preset service call");
  }
};

struct StormServices final : presonus::stormpanel_port::Dependencies {
  void cleanup() override { ++cleanupCalls; }
  void presetRecalled() override { fail(); }
  void fatChannelUpdate() override { fail(); }
  void fatMeterUpdate(ChannelComponent &) override { fail(); }
  Handle findGroup(int) override { fail(); }
  Handle byTag(Handle, int) override { fail(); }
  void setControl(Handle, int, int) override { fail(); }
  int count(Handle) override { fail(); }
  Handle at(Handle, int) override { fail(); }
  Handle asLED(Handle) override { fail(); }
  int tag(Handle) override { fail(); }
  void setBlinkMode(Handle, bool) override { fail(); }
  void blinkLED(int, std::uint32_t, bool) override { fail(); }
  MixerLCD *constructLCD(std::size_t) override { fail(); }
  void addBook(MixerLCD *, std::uint32_t, int) override { fail(); }
  int cleanupCalls = 0;

private:
  [[noreturn]] static void fail() {
    throw std::logic_error("Unexpected Storm service call");
  }
};

template <class T> auto objectBytes(const T &object) {
  std::array<unsigned char, sizeof(T)> snapshot;
  std::memcpy(snapshot.data(), &object, snapshot.size());
  return snapshot;
}

// Calls use a virtual member pointer on the real base reference so the
// descendant cases exercise their linked vtables.
using Callback = void (FrontPanelComponent::*)(const PresetComponent &, int);
static_assert(
    std::is_same_v<decltype(&FrontPanelComponent::presetStored), Callback>);
static_assert(std::is_same_v<decltype(&Fat24FrontPanelComponent::presetStored),
                             Callback>);
static_assert(std::is_same_v<decltype(&StormFrontPanelComponent::presetStored),
                             Callback>);

template <class T>
void replay(const char *owner, T &panel, const PresetComponent &preset,
            const PresetServices &presetServices,
            const StormServices &stormServices) {
  constexpr int indices[] = {std::numeric_limits<int>::min(), -1, 0, 7,
                             std::numeric_limits<int>::max()};
  auto &front = panel.portableFrontState();
  auto &base = panel.portableState();
  front.heldButton = 9;
  front.controlsBlocked = true;
  front.fatChannelDirty = true;
  base.active = true;
  const Callback callback = &FrontPanelComponent::presetStored;
  for (int index : indices) {
    const auto panelBefore = objectBytes(panel);
    const auto frontBefore = objectBytes(front);
    const auto presetBefore = objectBytes(preset);
    const auto componentBefore = objectBytes(base.component);
    auto &polymorphic = static_cast<FrontPanelComponent &>(panel);
    (polymorphic.*callback)(preset, index);
    const bool panelChanged = panelBefore != objectBytes(panel) ||
                              frontBefore != objectBytes(front) ||
                              componentBefore != objectBytes(base.component);
    std::cout << owner << ' ' << index << ' ' << panelChanged << ' '
              << (presetBefore != objectBytes(preset)) << ' '
              << (presetServices.teardownCalls + stormServices.cleanupCalls)
              << '\n';
  }
}
} // namespace

int main() {
  PresetServices presetServices;
  const Presonus::Panel::PresetComponent preset(presetServices);
  StormServices stormServices;
  Presonus::Panel::FrontPanelComponent base(
      Presonus::Panel::FrontPanelComponent::SourcePortConstruction{});
  Presonus::Panel::Fat24FrontPanelComponent fat(
      Presonus::Panel::Fat24FrontPanelComponent::SourcePortConstruction{});
  Presonus::Panel::StormFrontPanelComponent storm(stormServices);
  replay("FrontPanelComponent", base, preset, presetServices, stormServices);
  replay("Fat24FrontPanelComponent", fat, preset, presetServices,
         stormServices);
  replay("StormFrontPanelComponent", storm, preset, presetServices,
         stormServices);
}
