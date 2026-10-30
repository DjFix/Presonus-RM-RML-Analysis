#include "presonus/dice/programmer.hpp"
#include "presonus/dice/programmer_device_services.hpp"
#include <cassert>
#include <linux/spi/spidev.h>

namespace Presonus::DICE {
std::int32_t Dice3Programmer::open(const char *path) {
  assert(deviceServices_ != nullptr && services_ != nullptr);
  state_.descriptor = deviceServices_->openDevice(path, 2);
  if (state_.descriptor < 0)
    return 0;
  std::uint32_t mode = 0;
  if (deviceServices_->modeIoctl(state_.descriptor, SPI_IOC_RD_MODE, mode) < 0)
    return 0;
  mode &= ~std::uint32_t(3);
  if (deviceServices_->modeIoctl(state_.descriptor, SPI_IOC_WR_MODE, mode) < 0)
    return 0;
  // Preserve the original early-ioctl failure descriptor leak; no silent fix.
  auto pin100 = deviceServices_->makeOutputPin(100);
  pin100->set(0);
  services_->sleepMilliseconds(1);
  auto pin28 = deviceServices_->makeOutputPin(28);
  pin28->set(0);
  services_->sleepMilliseconds(1);
  if (readJedecId() != 0x2015) {
    if (state_.descriptor != -1) {
      deviceServices_->closeDevice(state_.descriptor);
      state_.descriptor = -1;
    }
    return 0;
  }
  return 1;
}

void Dice3Programmer::close() {
  assert(deviceServices_ != nullptr && services_ != nullptr);
  auto pin28 = deviceServices_->makeOutputPin(28);
  pin28->set(1);
  services_->sleepMilliseconds(1);
  auto pin100 = deviceServices_->makeOutputPin(100);
  pin100->set(1);
  services_->sleepMilliseconds(1);
  if (state_.descriptor != -1)
    deviceServices_->closeDevice(state_.descriptor);
  // Original does not reset the descriptor after close. RAII preserves pin
  // destruction order100 then28; original Panel C1/D1 C++ remains unresolved.
}
} // namespace Presonus::DICE
