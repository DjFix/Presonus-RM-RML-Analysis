#include "presonus/dice/manager.hpp"
#include "presonus/dice/manager_programmer_services.hpp"
#include <stdexcept>
namespace Presonus::DICE {
std::int32_t Dice3Manager::updateFirmware(UC::IFirmwareUpdateListener *listener,
                                          const unsigned char *image,
                                          int length) {
  if (!portableProgrammerServices_)
    throw std::logic_error("Dice3Manager programmer services are required");
  Dice3Programmer programmer(listener, image,
                             static_cast<unsigned int>(length));
  portableProgrammerServices_->prepare(programmer);
  if (programmer.open("/dev/spidev0.2") == 0)
    return -1;
  portableProgrammerServices_->invalidateSubsystemInfo();
  const auto result = programmer.update();
  programmer.close();
  return result;
}
std::int32_t Dice3Manager::eraseFirmware() {
  if (!portableProgrammerServices_)
    throw std::logic_error("Dice3Manager programmer services are required");
  Dice3Programmer programmer(nullptr, nullptr, 0);
  portableProgrammerServices_->prepare(programmer);
  if (programmer.open("/dev/spidev0.2") == 0)
    return -1;
  const auto result = programmer.eraseAll();
  programmer.close();
  return result;
}
} // namespace Presonus::DICE
