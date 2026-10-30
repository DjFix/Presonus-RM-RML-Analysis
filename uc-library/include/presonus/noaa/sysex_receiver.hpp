#pragma once
#include "presonus/dice/packet_services.hpp"
#include "presonus/dice/response_services.hpp"
#include "presonus/noaa/spi_packets.hpp"

namespace Presonus::NOAA {
// Original RTTI: ISysexReceiver base, slots receive / pure accepts / post.
// Portable storage differs from the original ARM layout. No virtual destructor
// is introduced. Ordinary receive/post return spellings remain pending.
class SysexReceiver : public ISysexReceiver {
public:
  SysexReceiver();
  void receive(const SysexPacket &packet) override;
  virtual void post(SysexPacket &packet);
  unsigned char waitAck(long long timeout);
  bool waitResponseSet(unsigned int &response, long long timeout);
  presonus::dice::SubsystemState &portableState() { return state_; }
  void setPortableResponseServices(presonus::dice::ResponseServices &services) {
    services_ = &services;
  }

private:
  // infoWords[0] represents the response word zeroed by constructor/post.
  // Other SubsystemState members are independent portable storage.
  presonus::dice::SubsystemState state_;
  presonus::dice::ResponseServices *services_ = nullptr;
};
} // namespace Presonus::NOAA
