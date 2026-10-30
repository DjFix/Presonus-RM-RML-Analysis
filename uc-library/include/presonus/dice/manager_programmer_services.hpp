#pragma once
#include "presonus/dice/packet_services.hpp"
#include "presonus/dice/programmer.hpp"
#include "presonus/dice/programmer_device_services.hpp"
namespace presonus::dice {
// Independent required source-port boundary, not original Manager layout/API.
class ManagerProgrammerServices {
public:
  virtual ~ManagerProgrammerServices() = default;
  virtual void prepare(Presonus::DICE::Dice3Programmer &programmer) = 0;
  virtual void invalidateSubsystemInfo() = 0;
};
// Borrow real Programmer providers. Production composition uses
// CclProgrammerServices and LinuxProgrammerDeviceServices; there is no default
// successful provider and no fabricated legacy Core/Panel implementation.
class BoundManagerProgrammerServices final : public ManagerProgrammerServices {
public:
  BoundManagerProgrammerServices(ProgrammerServices &runtime,
                                 ProgrammerDeviceServices &device,
                                 SubsystemState &subsystem,
                                 ProgressSink *progress = nullptr)
      : runtime_(runtime), device_(device), subsystem_(subsystem),
        progress_(progress) {}
  void prepare(Presonus::DICE::Dice3Programmer &programmer) override;
  void invalidateSubsystemInfo() override;

private:
  ProgrammerServices &runtime_;
  ProgrammerDeviceServices &device_;
  SubsystemState &subsystem_;
  ProgressSink *progress_;
};
} // namespace presonus::dice
