#include "core/system/coredebug.h"
#include "presonus/noaa/spi_packets.hpp"
#include <cerrno>
#include <cstdio>
#include <fcntl.h>
#include <linux/spi/spidev.h>
#include <sys/ioctl.h>
#include <unistd.h>

DEFINE_SINGLETON(Presonus::NOAA::TCardSPI)

namespace presonus::noaa {
namespace {
class LinuxSpiIO final : public SpiServiceIO {
public:
  int open(const char *path, int flags) override { return ::open(path, flags); }
  int maxSpeed(int descriptor, std::uint32_t speed) override {
    return ::ioctl(descriptor, SPI_IOC_WR_MAX_SPEED_HZ, &speed);
  }
  int transfer(int descriptor, const SpiTransfer &logical) override {
    spi_ioc_transfer transfer{};
    transfer.tx_buf = reinterpret_cast<std::uintptr_t>(logical.tx);
    transfer.rx_buf = reinterpret_cast<std::uintptr_t>(logical.rx);
    transfer.len = logical.length;
    transfer.speed_hz = logical.speed;
    transfer.delay_usecs = logical.delay;
    transfer.bits_per_word = logical.bits;
    transfer.cs_change = logical.csChange;
    return ::ioctl(descriptor, SPI_IOC_MESSAGE(1), &transfer);
  }
  int close(int descriptor) override { return ::close(descriptor); }
  int errorNumber() override { return errno; }
  std::int64_t rawTicks() override {
    return presonus::dice::packetClockRawTicks();
  }
  void diagnostic(bool standardOutput, const char *format, int value,
                  bool hasArgument) override {
    if (standardOutput) {
      if (hasArgument)
        std::printf(format, value);
      else
        std::printf("%s", format);
    } else {
      if (hasArgument)
        Core::DebugPrintf(format, value);
      else
        Core::DebugPrintf("%s", format);
    }
  }
};
thread_local SpiServiceIO *overrideIO = nullptr;
} // namespace
SpiServiceIO &spiServiceConstructionIO() {
  static LinuxSpiIO provider;
  return overrideIO ? *overrideIO : provider;
}
SpiServiceIO *setSpiServiceConstructionIO(SpiServiceIO *io) {
  auto *previous = overrideIO;
  overrideIO = io;
  return previous;
}
} // namespace presonus::noaa

namespace Presonus::NOAA {
TCardSPI::TCardSPI()
    : ownedState_(std::in_place, std::array<unsigned char, 256>{}, 0, 0, 0),
      state_(*ownedState_), io_(&presonus::noaa::spiServiceConstructionIO()) {
  auto *pin = new Panel::InputPin(-1, nullptr);
  pin->setup(34, this);
  if (pinCount_ < pins_.size())
    pins_[pinCount_++] = pin;
  pin = new Panel::InputPin(-1, nullptr);
  pin->setup(137, this);
  if (pinCount_ < pins_.size())
    pins_[pinCount_++] = pin;
}
TCardSPI::~TCardSPI() {
  // Borrowed state has independent lifetime and no owned GPIO/descriptor.
  if (!ownedState_)
    return;
  Core::Threads::ScopedLock guard(state_.lock);
  for (unsigned i = 0; i < pinCount_; ++i)
    delete pins_[i];
  if (descriptor_ != -1)
    io_->close(descriptor_);
  descriptor_ = -1;
  // Actual CCL member and Singleton base destruction follows the body.
}
int TCardSPI::open(const char *path) {
  if (descriptor_ != -1)
    return 1;
  descriptor_ = io_->open(path, O_RDWR);
  if (descriptor_ < 0) {
    io_->diagnostic(true, "error opening NOAA device %d\n", descriptor_, true);
    return 0;
  }
  if (io_->maxSpeed(descriptor_, 20000000) < 0) {
    io_->diagnostic(true, "error: SPI max_speed_hz", 0, false);
    return 0;
  }
  return 1;
}
void TCardSPI::post(SysexPacket &packet) {
  Core::Threads::ScopedLock guard(state_.lock);
  const auto ticks = io_->rawTicks() / 1000000;
  const auto bits = static_cast<std::uint64_t>(ticks);
  packet.portableMetadata().trailingWords[2] = static_cast<std::uint32_t>(bits);
  packet.portableMetadata().trailingWords[3] =
      static_cast<std::uint32_t>(bits >> 32);
  std::array<unsigned char, 256> tx, rx;
  if (packet.length != 0)
    std::memcpy(tx.data(), packet.bytes.data(), packet.length);
  const int received =
      io_->transfer(descriptor_, {tx.data(), rx.data(), packet.length});
  if (received < 0) {
    io_->diagnostic(false, "\nSPI error: SPI_IOC_MESSAGE: %d\n",
                    io_->errorNumber(), true);
    return;
  }
  if (received == 0) {
    io_->diagnostic(false, "**ERR SPI\n", 0, false);
    return;
  }
  if (received > int(rx.size())) {
    // Explicit portable guard for original out-of-stack-buffer result domain.
    // It is excluded from original behavioral equivalence.
    ++rejectedTransferResults_;
    return;
  }
  bool dataSeen = false;
  for (int i = 0; i < received; ++i) {
    if (rx[i] == 0xf8)
      continue;
    assembleSYSEX(rx.data() + i, 1);
    dataSeen = true;
  }
  if (dataSeen)
    idleRead();
}
void TCardSPI::idleRead() {
  Core::Threads::ScopedLock guard(state_.lock);
  const std::array<unsigned char, 3> tx{0xf8, 0xf8, 0xf8};
  while (state_.disabled == 0) {
    std::array<unsigned char, 3> rx{0xf8, 0xf8, 0xf8};
    const int result = io_->transfer(descriptor_, {tx.data(), rx.data(), 2});
    if (result < 0) {
      io_->diagnostic(false, "\nSPI error: SPI_IOC_MESSAGE: %d\n",
                      io_->errorNumber(), true);
      return;
    }
    const bool firstIdle = rx[0] == 0xf8 || rx[0] == 0xff;
    if (!firstIdle)
      assembleSYSEX(rx.data(), 1);
    if (rx[1] != 0xf8 && rx[1] != 0xff)
      assembleSYSEX(rx.data() + 1, 1);
    else if (firstIdle)
      return;
  }
}
void TCardSPI::idleReadPin() {
  // The original snapshots count/list once; arbitrary destructive reentrancy
  // while iterating is outside the defined tested domain.
  const unsigned count = pinCount_;
  auto *const pins = pins_.data();
  for (unsigned i = 0; i < count; ++i)
    pins[i]->read();
}
void TCardSPI::onIdle(bool readSpi) {
  idleReadPin();
  if (readSpi)
    idleRead();
}
void TCardSPI::pinStateChanged(int pin, int value) {
  if (pin == 137 && value != 0)
    idleRead();
}
} // namespace Presonus::NOAA
