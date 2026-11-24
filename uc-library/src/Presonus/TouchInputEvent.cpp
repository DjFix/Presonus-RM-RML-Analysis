#include "presonus/surface/DisplayManager.hpp"

namespace Presonus {
void TouchInputEvent::fromMsg(Touchscreen_Type &message) {
  const auto *bytes = reinterpret_cast<const unsigned char *>(&message);
  const unsigned packed = bytes[3];
  screen = packed >> 4;
  x = bytes[1] | ((packed & 0x0c) << 6);
  y = bytes[2] | ((packed & 0x03) << 8);

  switch (bytes[0]) {
  case 'U':
    type = 2;
    break;
  case 'z':
    type = 1;
    break;
  default:
    type = 0;
    break;
  }
}
} // namespace Presonus
