#include "presonus/McuVpotControl.hpp"

namespace Presonus {
McuVpotControl::McuVpotControl(const Core::TRect<int> &size,
                               Core::Portable::Parameter *parameter)
    : Core::Portable::Slider(size, parameter), value_(0) {}

McuVpotControl::PortableState McuVpotControl::portableState() const {
  return {image_.getBitmap(), strip_.getBitmap(), slice_.getBitmap(), value_};
}
} // namespace Presonus
