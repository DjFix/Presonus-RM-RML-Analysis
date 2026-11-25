#include "presonus/panel/SPIControl.hpp"
#include "presonus/panel/protocol_comm.hpp"

namespace Presonus::Panel {
SPIControl::SPIControl(int tag) : SPIControl(tag, 0, 0) {}

SPIControl::SPIControl(int tag, int group, int match)
    : LEDControl(tag, group, match) {}

SPIControl::~SPIControl() = default;
void SPIControl::broadcastValue(int value) {
  auto &last = presonus::panel::ControlAccess::lastLevel(*this);
  if (last == value)
    return;
  last = value;
  presonus::panel::ControlAccess::io(*this)->broadcast(this);
}
} // namespace Presonus::Panel
