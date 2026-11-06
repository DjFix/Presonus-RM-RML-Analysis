#pragma once
#include "core/portable/gui/corecontrols.h"
namespace Presonus::Surface {
// Intentional source port on actual pinned CCL RadioButton. Native field
// offsets/inheritance and ARM ABI are not established by this class definition.
class RadioToggleButton : public Core::Portable::RadioButton {
public:
  explicit RadioToggleButton(Core::RectRef size = Core::Rect(),
                             Core::Portable::Parameter *p = nullptr,
                             int radioValue = 0, int offValue = 0)
      : Core::Portable::RadioButton(size, p, radioValue), offValue_(offValue) {}
  ~RadioToggleButton() override;
  void push() override;
  void setOffValue(int v) { offValue_ = v; }
  int getOffValue() const { return offValue_; }

private:
  int offValue_;
};
} // namespace Presonus::Surface
