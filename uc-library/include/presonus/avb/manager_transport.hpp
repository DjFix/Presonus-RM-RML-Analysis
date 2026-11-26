#pragma once
#include "presonus/avb/protocol.hpp"
#include "presonus/dice/response_services.hpp"

namespace presonus::avb {
// Independent application interface, never an original manager/base ABI.
// Only the final typed DICE/NOAA adapters implement this production interface.
// This common header owns no role receiver, packet or hardware transport.
// Bind the manager context first. Manager and app pump outlive this adapter;
// operations and adapter lifetime are serialized by the application.
class ManagerTransport {
public:
  virtual ~ManagerTransport();
  ManagerTransport(const ManagerTransport &) = delete;
  ManagerTransport &operator=(const ManagerTransport &) = delete;
  Presonus::AVB::AvbManagerBase::Role role() const { return role_; }
  int transact(unsigned char *bytes, unsigned char length);

protected:
  ManagerTransport(Presonus::AVB::AvbManagerBase &manager,
                   Presonus::AVB::AvbManagerBase::Role role,
                   dice::IdlePump &pump);
  // Concrete adapters must construct/post/wait through their actual providers;
  // this is not a success/ACK callback or an original recovered interface.
  virtual int postAndWait(unsigned char *bytes, unsigned char length) = 0;
  void receivePacket(const Presonus::DICE::SysexPacket &packet);
  void receivePacket(const Presonus::NOAA::SysexPacket &packet);
  struct ResponseState {
    unsigned char command;
    unsigned char status;
  };
  ResponseState responseState() const;
  Presonus::AVB::AvbManagerBase &manager_;
  dice::CclResponseServices services_;

private:
  friend class Presonus::AVB::AvbManagerBase;
  const Presonus::AVB::AvbManagerBase::Role role_;
};
} // namespace presonus::avb
