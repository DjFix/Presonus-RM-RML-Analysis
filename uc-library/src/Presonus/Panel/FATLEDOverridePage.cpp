#include "presonus/panel/FATLEDOverridePage.hpp"
namespace Presonus::Panel {
void FATLEDOverridePage::deactivate() {
  if (overrideParameter_)
    overrideParameter_->setValue(0.f, false);
}
} // namespace Presonus::Panel
