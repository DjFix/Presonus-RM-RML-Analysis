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
} // namespace presonus::panel
namespace Presonus::Panel {
// Partial portable interface. Original declaration, layout and ARM ABI remain
// bounded by existing evidence; this migration changes source organization
// only.
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
} // namespace Presonus::Panel
