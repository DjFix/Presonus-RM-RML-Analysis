#pragma once
#include "presonus/avb/manager_transport.hpp"
#include "presonus/noaa/sysex_receiver.hpp"

namespace presonus::avb {
// RM-only actual NOAA receiver/SPI composition. Initialized matching SPI
// singleton and borrowed app pump/SPI must outlive operations and destruction.
class NoaaManagerTransport final : public ManagerTransport {
public:
  NoaaManagerTransport(Presonus::AVB::AvbManagerBase &manager,
                       Presonus::NOAA::TCardSPI &spi, dice::IdlePump &pump);
  ~NoaaManagerTransport() override;

private:
  class Receiver final : public Presonus::NOAA::SysexReceiver {
  public:
    explicit Receiver(NoaaManagerTransport &owner) : owner_(owner) {}
    bool accepts(const Presonus::NOAA::SysexPacket &packet) override;
    void receive(const Presonus::NOAA::SysexPacket &packet) override;

  private:
    NoaaManagerTransport &owner_;
  };
  int postAndWait(unsigned char *bytes, unsigned char length) override;
  Presonus::NOAA::TCardSPI &spi_;
  Receiver receiver_;
};
} // namespace presonus::avb
