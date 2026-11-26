#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/IFaderPanel.hpp"
// Intentional partial source-port classes. The application destructor ranges
// only reset dispatch pointers and call Component destruction. Using the real
// pinned provider as a base models that cleanup; original inheritance, complete
// fields, vtable addresses and ARM32 layout are not established.
namespace Presonus {
class MackieControlComponent : public Core::Portable::Component,
                               public IFaderPanel::LocalUpdates {
public:
  ~MackieControlComponent();
  // Source-port contract: a borrowed pointer to this component's actual model.
  // Original return type and embedded ARM offset are not a layout guarantee.
  MackieControlModel *getModel();
  // Parameter updates use the pinned Component provider. Original unencoded
  // return declarations remain unresolved; void is the source-port contract.
  // Portable void callbacks; exact original return declaration is unresolved.
  virtual void updateDisplayStyle(int tag, int style, bool enabled);
  virtual void updateLedColor(int tag, int color);
  void updateLedState(int tag, int state) override;
  void updateTextDisplay(int tag, const char *text, int unused) override;
  void updateFader(int tag, float value) override;
  void updateMeter(int tag, float value) override;
  void updateValueBar(int tag, int mode, float value, bool enabled) override;
  void paramChanged(Core::Portable::Parameter *parameter, int message) override;
  // Borrowed actual NumericParam, independent source-port counterpart of native
  // master pointer. Initialization below is source setup, not recovered ctor.
  Core::Portable::NumericParam *masterFader = nullptr;
  MackieControlModel model;

private:
  // Real pinned providers cache collection indices, including misses. The
  // inherited paramList remains the only collection. Valid caller offsets must
  // keep provider index addition in int range; shared error sentinel stays
  // null.
  Core::Portable::ParamArrayAccessor faders_{0x2000};
  Core::Portable::ParamArrayAccessor meters_{0};
  Core::Portable::ParamArrayAccessor valueBarModes_{0x4400};
  Core::Portable::ParamArrayAccessor valueBarValues_{0x4500};
  Core::Portable::ParamArrayAccessor valueBarFlags_{0x4600};
};
} // namespace Presonus
