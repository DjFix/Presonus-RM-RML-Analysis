#pragma once
#include "presonus/dice/sysex.hpp"
namespace presonus::dice::fixture {
// Independent concrete fixture; original SysexReceiver remains abstract.
class ConcreteReceiver : public Presonus::DICE::SysexReceiver {
public:
  bool accepts(const Presonus::DICE::SysexPacket &) override { return false; }
};
} // namespace presonus::dice::fixture
