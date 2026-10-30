#include "presonus/uc/midi_connection.hpp"

namespace Presonus::UC {
MidiConnection::MidiConnection() : handler_(nullptr) {}

MidiConnection::~MidiConnection() = default;

bool MidiConnection::deliver(const MidiEvent &event) {
  if (!handler_)
    return false;
  handler_->handleMidiEvent(event);
  return true;
}
} // namespace Presonus::UC
