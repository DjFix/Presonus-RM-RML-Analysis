#pragma once
#include "presonus/panel/PresetComponent.hpp"
#include "presonus/panel/PresetNameManager.hpp"
#include "presonus/panel/control.hpp"
#include "presonus/trial08/FXPresetRecallComponent.hpp"
#include "presonus/uc/file_services.hpp"

// Partial portable source classes, based on observed base cleanup calls.
// Complete original declarations, layout and ARM ABI are not established.
class MixerSceneLoader : public Presonus::UC::FileRequestHandler {
public:
  using FileRequestHandler::FileRequestHandler;
  ~MixerSceneLoader() override;
};
namespace Presonus::Panel {
class SPIControl : public Control {
public:
  using Control::Control;
  ~SPIControl() override;
};
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
