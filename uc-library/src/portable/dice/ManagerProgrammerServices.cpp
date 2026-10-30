#include "presonus/dice/manager_programmer_services.hpp"
namespace presonus::dice {
void BoundManagerProgrammerServices::prepare(
    Presonus::DICE::Dice3Programmer &programmer) {
  programmer.bindProgrammerServices(runtime_, -1);
  programmer.bindProgrammerDeviceServices(device_);
  if (progress_)
    programmer.bindProgressSink(*progress_);
}
void BoundManagerProgrammerServices::invalidateSubsystemInfo() {
  // Existing portable infoWords[0] corresponds to original subsystem offset0xc.
  // This is an intentional source-port mapping, not a host/ARM layout claim.
  subsystem_.infoWords[0] = 0xffffffffU;
}
} // namespace presonus::dice
