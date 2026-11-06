#pragma once
#include "presonus/panel/FXPresetRecallComponent.hpp"
#include "presonus/panel/PresetComponent.hpp"
#include <memory>

// Partial portable source class. Original declarations, layout and ARM ABI
// remain limited to the existing evidence; this migration adds no ABI claim.
namespace presonus::panel {
struct FxPresetTestAccess;
}
namespace Presonus::Panel {
class FrontPanelComponent;
// Borrowed, fixed-extent collection models the observed array/count snapshot.
// Its lifetime and valid nonnull elements are caller preconditions, not an
// inference of original ownership or container declaration.
class FxPresetComponent {
public:
  FxPresetComponent(FXPresetRecallComponent *const *items, int count)
      : recalls(items, count) {}
  // Owning lifecycle mode is an explicit source adaptation using composition,
  // not a claim about the original inheritance or ARM object layout. Services,
  // parameter and child objects must outlive this object. Child pointers remain
  // borrowed; only their CCL vector storage is owned.
  FxPresetComponent(presonus::panel::PresetApplicationServices &services,
                    Core::Portable::Parameter *observed,
                    FXPresetRecallComponent *const *items, int count);
  FxPresetComponent(FrontPanelComponent &,
                    Presonus::Mixer::MixerComponentBase &);
  virtual ~FxPresetComponent();
  FxPresetComponent(const FxPresetComponent &) = delete;
  FxPresetComponent &operator=(const FxPresetComponent &) = delete;
  PresetComponent *sourcePortPreset() const { return preset.get(); }
  // Portable return choices; original ordinary returns remain unresolved.
  Core::Portable::Parameter *getRecallParameter(int, int);
  bool recall(Core::Portable::Attributes &, bool);
  void presetStored(const PresetComponent &, int);
  // Exact native body has no application side effects. Void is a source-port
  // return choice; unchanged native r0 does not establish a return declaration.
  void presetRecalled(const PresetComponent &, int);
  // Caller-owned source-port state; optional provider yields the observed zero
  // default for a missing FX selection parameter. No original field inference.
  Core::Portable::Component *fxParameters = nullptr;
  Core::CString256 presetType;
  bool presetTypeBound = false;
  // Selection notifications require sourcePortPreset()->sourcePortBindManager
  // with a concrete borrowed manager that outlives this object. Legacy borrowed
  // array/service modes retain their previous narrower API boundaries.
  void paramChanged(Core::Portable::Parameter *, int);
  int getFxIndex() const;
  const char *getPresetType() const;

private:
  friend struct presonus::panel::FxPresetTestAccess;
  // The legacy borrowed-array mode has no registration, vector allocation or
  // PresetComponent provider, and therefore a deliberately smaller lifecycle.
  std::unique_ptr<PresetComponent> preset;
  std::unique_ptr<Core::Vector<FXPresetRecallComponent *>> ownedRecalls;
  Core::Portable::Parameter *observed = nullptr;
  Core::ConstVector<FXPresetRecallComponent *> recalls;
  // Stable opaque membership token, never dereferenced as an original Delegate.
  unsigned char delegateToken = 0;
  FXPresetRecallComponent *currentChild = nullptr;
};
} // namespace Presonus::Panel
