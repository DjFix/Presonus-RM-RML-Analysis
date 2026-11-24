#pragma once

#include "presonus/MackieControlModel.hpp"
#include "presonus/uc/midi_connection.hpp"

namespace Presonus {
class IFaderUnit;
} // namespace Presonus

namespace Presonus::Surface {
// Portable adapter with a borrowed byte-message sink. The original return
// declaration and ARM object layout are unresolved.
class UCMidiInputAdapter : public UC::IMidiEventHandler {
public:
  explicit UCMidiInputAdapter(IMidiSink &sink) : sink_(sink) {}
  void handleMidiEvent(const UC::MidiEvent &event) override;

  // Borrowed binding; void is a portable declaration.
  void setFaderUnit(IFaderUnit *);

private:
  friend struct UCMidiInputAdapterReplayAccess;
  IMidiSink &sink_;
  IFaderUnit *faderUnit_ = nullptr;
};
} // namespace Presonus::Surface
