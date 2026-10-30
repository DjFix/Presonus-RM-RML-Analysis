#include "presonus/dice/manager_programmer_services.hpp"
#include <cstdarg>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <linux/spi/spidev.h>
namespace {
void check(bool x) {
  if (!x)
    std::abort();
}
unsigned opens = 0, closes = 0, transfers = 0, reports = 0;
class Progress final : public presonus::dice::ProgressSink {
public:
  void report(Presonus::UC::IFirmwareUpdateListener *listener, const char *text,
              float value) override {
    check(listener != nullptr && std::strcmp(text, "provider") == 0 &&
          value == 0.5F);
    ++reports;
  }
};
} // namespace
extern "C" int __wrap_open(const char *path, int flags, ...) {
  check(std::strcmp(path, "/dev/spidev0.2") == 0 && flags == O_RDWR);
  ++opens;
  return 73;
}
extern "C" int __wrap___open_2(const char *path, int flags) {
  return __wrap_open(path, flags);
}
extern "C" int __wrap_close(int fd) {
  check(fd == 73);
  ++closes;
  return 0;
}
extern "C" int __wrap_ioctl(int fd, unsigned long request, ...) {
  check(fd == -1 && request == SPI_IOC_MESSAGE(1));
  va_list args;
  va_start(args, request);
  auto *t = va_arg(args, spi_ioc_transfer *);
  va_end(args);
  check(t->len == 2 && t->speed_hz == 1000000 && t->bits_per_word == 8);
  auto *tx = reinterpret_cast<const unsigned char *>(t->tx_buf);
  auto *rx = reinterpret_cast<unsigned char *>(t->rx_buf);
  check(tx[0] == 0x9f && tx[1] == 0);
  rx[0] = 0x21;
  rx[1] = 0x43;
  ++transfers;
  return 2;
}
int main() {
  presonus::dice::LinuxProgrammerTransport transport;
  presonus::dice::CclProgrammerServices runtime(transport);
  presonus::dice::LinuxProgrammerDeviceServices device;
  presonus::dice::SubsystemState state;
  state.infoWords = {1, 2, 3};
  Progress progress;
  presonus::dice::BoundManagerProgrammerServices binding(runtime, device, state,
                                                         &progress);
  unsigned char token = 0, image = 0;
  Presonus::DICE::Dice3Programmer p(
      reinterpret_cast<Presonus::UC::IFirmwareUpdateListener *>(&token), &image,
      1);
  binding.prepare(p);
  check(p.inspectState().descriptor == -1);
  unsigned char tx = 0x9f, rx[2]{};
  check(p.performTransaction({&tx, 1, rx, 1}) == 0 && rx[0] == 0x21 &&
        rx[1] == 0x43);
  p.printProgress("provider", 0.5F, true);
  check(reports == 1);
  binding.invalidateSubsystemInfo();
  check(state.infoWords[0] == 0xffffffffU && state.infoWords[1] == 2 &&
        state.infoWords[2] == 3);
  const auto before = runtime.clockRawTicks();
  runtime.sleepMilliseconds(0);
  check(runtime.clockRawTicks() >= before);
  check(device.openDevice("/dev/spidev0.2", O_RDWR) == 73);
  check(device.closeDevice(73) == 0);
  check(opens == 1 && closes == 1 && transfers == 1);
  std::cout
      << "real CCL/Linux binding PASS; all fd/ioctl effects intercepted\n";
}
