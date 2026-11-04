#pragma once
#include "core/portable/corestorage.h"
#include "presonus/panel/PresetComponent.hpp"
#include "presonus/trial08/MixerComponentBase.hpp"
namespace presonus::panel {
// Explicit portable binding, never an ARM object layout. Selection uses the
// actual mixer provider index and caller-owned parameter components.
struct ChannelPresetState {
  Presonus::Mixer::MixerComponentBase &mixer;
  Core::ConstVector<Core::Portable::Component *> channels;
  const Core::Portable::IStorageFilter *filter;
  Core::Portable::Parameter *categoryFollow = nullptr;
  Core::Portable::Component &selected() const;
};
struct GeqPresetState {
  Core::ConstVector<Core::Portable::Component *> equalizers;
  Core::Portable::Parameter *selection = nullptr;
};
} // namespace presonus::panel
namespace Presonus::Panel {
// Partial portable interfaces. Full original declarations, layout and ARM ABI
// remain unresolved; inheritance follows observed base destruction calls.
class ChannelPresetComponent : public PresetComponent {
public:
  ChannelPresetComponent(presonus::panel::PresetApplicationServices &services,
                         presonus::panel::ChannelPresetState state)
      : PresetComponent(services), state(state) {}
  ~ChannelPresetComponent() override;
  virtual bool saveUserName() const;
  void updatePresetName() const override;
  void paramChanged(Core::Portable::Parameter *, int) override;
  bool recall(Core::Portable::Attributes &, bool);
  bool store();

private:
  presonus::panel::ChannelPresetState state;
  const char *getCategory(int);
  void categoryChanged();
  void slotChanged(int);
};
class GeqPresetComponent : public PresetComponent {
public:
  GeqPresetComponent(presonus::panel::PresetApplicationServices &services,
                     presonus::panel::GeqPresetState state)
      : PresetComponent(services), state(state) {}
  ~GeqPresetComponent() override;
  bool recall(Core::Portable::Attributes &, bool);

private:
  presonus::panel::GeqPresetState state;
};
class ScenesComponent : public PresetComponent {
public:
  ScenesComponent(presonus::panel::PresetApplicationServices &services,
                  Presonus::Mixer::MixerComponentBase &mixer)
      : PresetComponent(services), mixer(mixer) {}
  ~ScenesComponent() override;
  bool store();

private:
  Presonus::Mixer::MixerComponentBase &mixer;
};
} // namespace Presonus::Panel
