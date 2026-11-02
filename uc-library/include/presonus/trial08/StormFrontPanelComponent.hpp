#pragma once
#include <cstddef>
#include <cstdint>
namespace Presonus {
class StormMixSceneComponent;
class StormMuteGroupComponent;
namespace Mixer {
class ChannelComponent;
}
namespace Panel {
class MixerLCD;
}
} // namespace Presonus
namespace presonus::stormpanel_port {
// Required application adapter, independent of original layout/inheritance.
// Handles identify borrowed provider objects; zero denotes absent controls.
using Handle = std::uintptr_t;
struct Dependencies {
  virtual ~Dependencies() = default;
  virtual void cleanup() = 0;
  virtual void presetRecalled() = 0;
  virtual void fatChannelUpdate() = 0;
  virtual void fatMeterUpdate(Presonus::Mixer::ChannelComponent &) = 0;
  virtual Handle findGroup(int group) = 0;
  virtual Handle byTag(Handle group, int tag) = 0;
  virtual void setControl(Handle control, int value, int options) = 0;
  virtual int count(Handle group) = 0;
  virtual Handle at(Handle group, int index) = 0;
  virtual Handle asLED(Handle control) = 0;
  virtual int tag(Handle led) = 0;
  virtual void setBlinkMode(Handle led, bool enabled) = 0;
  virtual void blinkLED(int group, std::uint32_t tag, bool enabled) = 0;
  // Provider owns allocation/construction and exception cleanup. The original
  // ARM allocation size is evidence, not a portable sizeof(MixerLCD).
  virtual Presonus::Panel::MixerLCD *
  constructLCD(std::size_t armAllocationSize) = 0;
  virtual void addBook(Presonus::Panel::MixerLCD *, std::uint32_t originalTable,
                       int book) = 0;
};
} // namespace presonus::stormpanel_port
namespace Presonus::Panel {
// Portable source port. Original ordinary returns, inheritance, ownership and
// ARM32 layout remain unresolved. Every application service is required.
class StormFrontPanelComponent {
public:
  explicit StormFrontPanelComponent(presonus::stormpanel_port::Dependencies &d)
      : dependencies(d) {}
  void cleanup();
  void mixSceneRecalled(const Presonus::StormMixSceneComponent &);
  void mixSceneEnterStoreState(const Presonus::StormMixSceneComponent &);
  void mixSceneExitStoreState(const Presonus::StormMixSceneComponent &);
  void setMuteGroupDirty(const Presonus::StormMuteGroupComponent &, int, bool);
  void setAllMutesGroupDirty(const Presonus::StormMuteGroupComponent &, bool);
  void doFatChannelUpdate();
  MixerLCD *createLCD();
  void doFatMeterUpdate(Presonus::Mixer::ChannelComponent &);
  void blinkSceneButtons(bool);

private:
  presonus::stormpanel_port::Dependencies &dependencies;
};
} // namespace Presonus::Panel
