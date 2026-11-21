#pragma once

#include "presonus/MackieControlModel.hpp"
#include "presonus/uc/midi_connection.hpp"

namespace Presonus::Surface {
// Portable adapter with a borrowed byte-message sink. The original return
// declaration and ARM object layout are unresolved.
class UCMidiInputAdapter : public UC::IMidiEventHandler {
public:
  explicit UCMidiInputAdapter(IMidiSink &sink) : sink_(sink) {}
  void handleMidiEvent(const UC::MidiEvent &event) override;

private:
  IMidiSink &sink_;
};
} // namespace Presonus::Surface
