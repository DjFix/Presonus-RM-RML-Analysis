#pragma once
#include "core/portable/gui/corebitmap.h"
#include "core/portable/gui/corecontrols.h"
namespace Presonus {
// Portable CCL-backed contract. Original layout and unencoded returns pending.
class LinkControl : public Core::Portable::Control {
public:
  using Control::Control;
  bool isLinked() const;
  bool isRightSideOfLink() const;
  void setRightSideParam(Core::Portable::Parameter *p);
  void paramChanged(Core::Portable::Parameter *p, int msg) override;
  void setAttributes(const Core::Portable::Attributes &a) override;

protected:
  Core::Portable::Parameter *rightSideParam = nullptr;
  Core::Portable::BitmapReference leftImage, rightImage;
};
} // namespace Presonus
