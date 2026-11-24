#include "presonus/surface/UCMidiInputAdapter.hpp"

namespace Presonus::Surface {
void UCMidiInputAdapter::setFaderUnit(IFaderUnit *value) { faderUnit_ = value; }

void UCMidiInputAdapter::handleMidiEvent(const UC::MidiEvent &event) {
  if (event.sysexLength != 0) {
    sink_.sendMidiMessage(event.sysexData, event.sysexLength, 0);
    return;
  }

  const auto word = event.messageWord;
  const unsigned char bytes[] = {static_cast<unsigned char>(word),
                                 static_cast<unsigned char>(word >> 8),
                                 static_cast<unsigned char>(word >> 16)};
  sink_.sendMidiMessage(bytes, sizeof(bytes), 0);
}
} // namespace Presonus::Surface
