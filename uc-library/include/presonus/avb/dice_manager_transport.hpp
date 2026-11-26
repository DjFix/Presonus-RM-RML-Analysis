#pragma once
#include "presonus/avb/manager_transport.hpp"
#include "presonus/dice/sysex.hpp"
#include "presonus/dice/uart_assembly.hpp"

namespace presonus::avb {
// CS18-only actual DICE receiver/UART composition. Initialized matching UART
// singleton and borrowed app pump/UART must outlive operations and destruction.
class DiceManagerTransport final : public ManagerTransport {
public:
  DiceManagerTransport(Presonus::AVB::AvbManagerBase &manager,
                       Presonus::DICE::Dice3Uart &uart, dice::IdlePump &pump);
  ~DiceManagerTransport() override;

private:
  class Receiver final : public Presonus::DICE::SysexReceiver {
  public:
    explicit Receiver(DiceManagerTransport &owner) : owner_(owner) {}
    bool accepts(const Presonus::DICE::SysexPacket &packet) override;
    void receive(const Presonus::DICE::SysexPacket &packet) override;

  private:
    DiceManagerTransport &owner_;
  };
  int postAndWait(unsigned char *bytes, unsigned char length) override;
  Presonus::DICE::Dice3Uart &uart_;
  Receiver receiver_;
};
} // namespace presonus::avb
