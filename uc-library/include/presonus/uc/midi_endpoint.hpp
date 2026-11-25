#pragma once

#include "core/public/corestringbuffer.h"
#include "core/public/corevector.h"
#include "presonus/uc/midi_connection.hpp"

namespace presonus::uc {
struct MidiEndpointAccess;
}

namespace Presonus::UC {

// Portable projection from the recovered getInfo writes. The string fields
// borrow storage from the endpoint, and getInfo preserves the leading field.
struct MidiEndpointInfo {
  int preserved = 0;
  int type = 0;
  int firstId = 0;
  int secondId = 0;
  const char *firstName = nullptr;
  const char *secondName = nullptr;
};

// Partial portable abstract endpoint. Only the two abstract callbacks used by
// the recovered methods are declared here. Backends and ARM ABI are outside
// this interface.
class MidiEndpoint {
public:
  MidiEndpoint();
  virtual ~MidiEndpoint();

  void getInfo(MidiEndpointInfo &) const;
  MidiConnection *findConnectionForHandler(IMidiEventHandler *) const;
  bool sendFrom(const MidiEvent &);
  void addConnection(MidiConnection *);
  void removeConnection(MidiConnection *);

protected:
  virtual int getType() const = 0;
  virtual void onConnect(MidiConnection *, bool added) = 0;

private:
  Core::CString32 firstName_;
  Core::CString32 secondName_;
  int firstId_ = 0;
  int secondId_ = 0;
  Core::Vector<MidiConnection *> connections_;
  friend struct presonus::uc::MidiEndpointAccess;
};

} // namespace Presonus::UC

namespace presonus::uc {

struct MidiEndpointAccess {
  static auto &connections(Presonus::UC::MidiEndpoint &value) {
    return value.connections_;
  }
  static void setInfo(Presonus::UC::MidiEndpoint &value, int firstId,
                      int secondId, const char *firstName,
                      const char *secondName) {
    value.firstId_ = firstId;
    value.secondId_ = secondId;
    value.firstName_ = firstName;
    value.secondName_ = secondName;
  }
};

} // namespace presonus::uc
