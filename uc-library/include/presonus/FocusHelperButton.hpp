#pragma once

#include "core/portable/gui/corecontrols.h"

// Partial source port. Provider relationships are evidence-backed;
// these declarations do not establish firmware layouts or ARM ABI.
namespace Presonus {
class FocusHelperButton : public Core::Portable::RadioButton {
public:
  FocusHelperButton(const Core::TRect<int> &size,
                    Core::Portable::Parameter *parameter, int value);
  void setAttributes(const Core::Portable::Attributes &a) override;

  void paramChanged(Core::Portable::Parameter *p, int message) override;
  void restoreFocus();
  void draw(const Core::Portable::DrawEvent &e) override;
  void onIdle() override;

  // Independent portable observations. viewName_ borrows Attributes storage;
  // the hosting application must preserve that storage while using the pointer.
  const char *portableViewName() const { return viewName_; }
  bool portableActive() const { return active_; }

protected:
  bool active_;
  const char *viewName_;
};
} // namespace Presonus
