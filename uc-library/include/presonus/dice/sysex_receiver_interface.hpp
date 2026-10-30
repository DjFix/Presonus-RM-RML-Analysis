#pragma once
namespace Presonus::DICE {
class SysexPacket;
// Original RTTI/table proves this abstract two-slot interface; no ARM ABI
// claim.
class ISysexReceiver {
public:
  virtual void receive(const SysexPacket &) = 0;
  virtual bool accepts(const SysexPacket &) = 0;

protected:
  ~ISysexReceiver() = default;
};
} // namespace Presonus::DICE
