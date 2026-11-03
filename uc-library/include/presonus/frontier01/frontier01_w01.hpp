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

private:
  Core::ConstVector<FXPresetRecallComponent *> recalls;
};
} // namespace Presonus::Panel
