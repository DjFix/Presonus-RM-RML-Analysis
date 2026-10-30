#pragma once
#include "presonus/uc/events.hpp"
namespace Presonus::UC {
// Actual original two-slot interface name/order independently witnessed through
// BasicConnection's vtable and RTTI. bool is a portable declaration choice:
// ordinary return spellings are not encoded. No original ARM layout claim.
class IConnection {
public:
  virtual bool queueEvent(void *) = 0;
  virtual bool sendEvent(const Event &) = 0;

protected:
  ~IConnection() = default; // Original interface has no destructor slots.
};
// Seven pure slots independently named by SocketConnection::Channel's table.
// Parameter identities/constness/order retained; bool/int returns are portable
// choices matching admitted source methods, not original return declarations.
class IDataChannel {
public:
  virtual bool isReadable(int) = 0;
  virtual int getBytesAvailable() = 0;
  virtual int read(void *, int) = 0;
  virtual bool isWritable(int) = 0;
  virtual int getGranularity() = 0;
  virtual int write(const void *, int) = 0;
  virtual bool hasErrors(int) = 0;

protected:
  ~IDataChannel() = default; // Concrete Channel adds its own virtual D1/D0.
};
} // namespace Presonus::UC
