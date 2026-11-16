#pragma once
#include "core/portable/corestorage.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/PresetComponent.hpp"

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
  explicit ChannelPresetComponent(Presonus::Mixer::MixerComponentBase &mixer);
  // Independent views for later operations; construction keeps these empty.
  // The mixer and every bound object must outlive this component.
  void sourcePortBindChannelView(
      Core::ConstVector<Core::Portable::Component *> channels,
      const Core::Portable::IStorageFilter *filter,
      Core::Portable::Parameter *categoryFollow) {
    state.channels = channels;
    state.filter = filter;
    state.categoryFollow = categoryFollow;
  }
  Core::Portable::ListParam *sourcePortCategoryParameter() const {
    return categoryParameter_;
  }
  ChannelPresetComponent(presonus::panel::PresetApplicationServices &services,
                         presonus::panel::ChannelPresetState state)
      : PresetComponent(services), state(state) {}
  ~ChannelPresetComponent() override;
  virtual bool saveUserName() const;
  void updatePresetName() const override;
  void paramChanged(Core::Portable::Parameter *, int) override;
  bool recall(Core::Portable::Attributes &, bool);
  bool store();
  // Portable void declaration; original return spelling is unencoded.
  void onPresetCategoryChanged();

private:
  presonus::panel::ChannelPresetState state;
  // Independent cached real CCL type; no original subobject offset claim.
  Core::Portable::ListParam *categoryParameter_ = nullptr;
  const char *getCategory(int);
  void categoryChanged();
  void slotChanged(int);
};
} // namespace Presonus::Panel
