#pragma once

#include "core/public/corebitset.h"
#include "core/public/corevector.h"

namespace Presonus::UC {
class MidiEndpoint;
class IMidiNetworkListener;

// Portable composition of the observed sender-ID allocator and three rosters.
// Borrowed pointers remain owned by their callers. Native layout and base
// topology are outside this source port.
class MidiEndpointRegistry {
public:
  MidiEndpointRegistry();
  ~MidiEndpointRegistry();

  // The original ordinary return declarations remain unresolved.
  bool hasListeners() const;
  void removeListener(IMidiNetworkListener *listener);

  Core::IDSet &portableSenderIds() { return senderIds_; }
  Core::Vector<MidiEndpoint *> &portableLocalEndpoints() { return local_; }
  Core::Vector<MidiEndpoint *> &portableRemoteEndpoints() { return remote_; }
  Core::Vector<IMidiNetworkListener *> &portableListeners() {
    return listeners_;
  }

private:
  Core::IDSet senderIds_;
  Core::Vector<MidiEndpoint *> local_;
  Core::Vector<MidiEndpoint *> remote_;
  Core::Vector<IMidiNetworkListener *> listeners_;
};
} // namespace Presonus::UC
