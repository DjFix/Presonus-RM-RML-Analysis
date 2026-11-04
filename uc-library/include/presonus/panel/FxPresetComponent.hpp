#pragma once
#include "presonus/panel/PresetComponent.hpp"
#include "presonus/trial08/FXPresetRecallComponent.hpp"

// Partial portable source class. Original declarations, layout and ARM ABI
// remain limited to the existing evidence; this migration adds no ABI claim.
namespace Presonus::Panel {
// Borrowed, fixed-extent collection models the observed array/count snapshot.
// Its lifetime and valid nonnull elements are caller preconditions, not an
// inference of original ownership or container declaration.
class FxPresetComponent {
public:
  FxPresetComponent(FXPresetRecallComponent *const *items, int count)
      : recalls(items, count) {}
  void presetStored(const PresetComponent &, int);
  // Caller-owned source-port state; optional provider yields the observed zero
  // default for a missing FX selection parameter. No original field inference.
  Core::Portable::Component *fxParameters = nullptr;
  Core::CString256 presetType;
  bool presetTypeBound = false;
  int getFxIndex() const;
  const char *getPresetType() const;

private:
  Core::ConstVector<FXPresetRecallComponent *> recalls;
};
} // namespace Presonus::Panel
