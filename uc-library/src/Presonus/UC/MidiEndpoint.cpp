#include "presonus/uc/midi_endpoint.hpp"
#include <new>

namespace Presonus::UC {

MidiEndpoint::MidiEndpoint() : connections_(0, 5) {}
MidiEndpoint::~MidiEndpoint() = default;

void MidiEndpoint::getInfo(MidiEndpointInfo &info) const {
  info.type = getType();
  info.firstId = firstId_;
  info.secondId = secondId_;
  info.firstName = firstName_;
  info.secondName = secondName_;
}

MidiConnection *
MidiEndpoint::findConnectionForHandler(IMidiEventHandler *handler) const {
  for (auto *connection : connections_)
    if (connection->portableHandler() == handler)
      return connection;
  return nullptr;
}

bool MidiEndpoint::sendFrom(const MidiEvent &event) {
  bool delivered = true;
  for (auto *connection : connections_)
    if (!connection->deliver(event))
      delivered = false;
  return delivered;
}

void MidiEndpoint::addConnection(MidiConnection *connection) {
  const int count = connections_.count();
  // Native resize reports allocation failure as false and still notifies.
  bool haveRoom = count < connections_.getCapacity();
  if (!haveRoom) {
    try {
      haveRoom = connections_.resize(count + 1);
    } catch (const std::bad_alloc &) {
    }
  }
  if (haveRoom)
    connections_.add(connection);
  onConnect(connection, true);
}

void MidiEndpoint::removeConnection(MidiConnection *connection) {
  onConnect(connection, false);
  connections_.remove(connection);
}

} // namespace Presonus::UC
