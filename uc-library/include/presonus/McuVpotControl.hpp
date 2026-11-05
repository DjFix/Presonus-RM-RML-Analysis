#pragma once

#include "core/portable/gui/corecontrols.h"
#include "core/portable/gui/coreviewcontroller.h"

// Partial source port. Provider relationships are evidence-backed;
// these declarations do not establish firmware layouts or ARM ABI.
namespace Presonus {
class McuVpotControl : public Core::Portable::Slider {
public:
  McuVpotControl(const Core::TRect<int> &size,
                 Core::Portable::Parameter *parameter);
  // Source-port lifecycle extension; no original destructor identity claimed.
  ~McuVpotControl();
  void setAttributes(const Core::Portable::Attributes &) override;
  // Independent borrowed controller binding. If absent, use the real CCL
  // ViewBuilder scoped current controller while attributes are being built.
  void configurePortableController(Core::Portable::ViewController *c) {
    portableController_ = c;
  }
  void paramChanged(Core::Portable::Parameter *, int) override;
  void setDotParameter(Core::Portable::Parameter *);
  void setStyleParameter(Core::Portable::Parameter *);
  struct PortableState {
    Core::Portable::Bitmap *image;
    Core::Portable::Bitmap *strip;
    Core::Portable::Bitmap *slice;
    int value;
    Core::Portable::Parameter *styleParameter;
    Core::Portable::Parameter *dotParameter;
  };
  PortableState portableState() const;

protected:
  Core::Portable::BitmapReference image_, strip_, slice_;
  int value_;
  // Borrowed observer subjects; these members do not reproduce ARM offsets.
  Core::Portable::ViewController *portableController_ = nullptr;
  Core::Portable::Parameter *styleParameter_ = nullptr;
  Core::Portable::Parameter *dotParameter_ = nullptr;
};
} // namespace Presonus
