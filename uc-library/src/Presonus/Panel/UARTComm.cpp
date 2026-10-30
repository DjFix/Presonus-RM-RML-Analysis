#if !defined(__linux__)
#error "This UARTComm source port is validated for Linux POSIX APIs only."
#endif
#include "core/system/coredebug.h"
#include "presonus/dice/packet_services.hpp"
#include "presonus/panel/uart_comm.hpp"
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>

namespace presonus::panel {
namespace {
int result32(ssize_t value) {
  static_assert(sizeof(int) == sizeof(std::uint32_t));
  const std::uint32_t bits = static_cast<std::uint32_t>(value);
  int result;
  std::memcpy(&result, &bits, sizeof(result));
  return result;
}
class PosixUartServices final : public UartServices {
public:
  int openFile(const char *path, int flags) override {
    return ::open(path, flags);
  }
  int closeFile(int descriptor) override { return ::close(descriptor); }
  int readFile(int descriptor, void *buffer, std::uint32_t size) override {
    return result32(::read(descriptor, buffer, size));
  }
  int writeFile(int descriptor, const void *buffer,
                std::uint32_t size) override {
    return result32(::write(descriptor, buffer, size));
  }
  int exclusive(int descriptor, unsigned long request) override {
    return ::ioctl(descriptor, request);
  }
  int getAttributes(int descriptor, termios &attributes) override {
    return ::tcgetattr(descriptor, &attributes);
  }
  void makeRaw(termios &attributes) override { ::cfmakeraw(&attributes); }
  int setSpeed(termios &attributes, speed_t speed) override {
    return ::cfsetspeed(&attributes, speed);
  }
  int setAttributes(int descriptor, int action,
                    const termios &attributes) override {
    return ::tcsetattr(descriptor, action, &attributes);
  }
  int setFlags(int descriptor, int command, int flags) override {
    return ::fcntl(descriptor, command, flags);
  }
  void printError(const char *prefix) override { ::perror(prefix); }
  std::int64_t rawTicks() override {
    return presonus::dice::packetClockRawTicks();
  }
};
} // namespace
UartServices &systemUartServices() {
  static PosixUartServices services;
  return services;
}
} // namespace presonus::panel

namespace Presonus::Panel {
UARTComm::UARTComm()
    : ProtocolComm(), descriptor_(-1),
      services_(&presonus::panel::systemUartServices()) {}

UARTComm::~UARTComm() { close(); }

int UARTComm::read(char *buffer, int size) {
  Core::Threads::ScopedLock guard(lock_);
  const auto result = services_->readFile(descriptor_, buffer,
                                          static_cast<std::uint32_t>(size));
  if (result < 0)
    services_->printError("UARTComm: ");
  return result;
}

int UARTComm::write(const char *buffer, int size) {
  Core::Threads::ScopedLock guard(lock_);
  const auto result = services_->writeFile(descriptor_, buffer,
                                           static_cast<std::uint32_t>(size));
  if (result != size)
    Core::DebugPrintf("write failed:%d\n", result);
  return result;
}

void UARTComm::close() {
  Core::Threads::ScopedLock guard(lock_);
  if (descriptor_ != -1)
    services_->closeFile(descriptor_);
  Core::DebugPrintf("UART: close port %d\n", descriptor_);
  descriptor_ = -1;
}

int UARTComm::open(const char *path) {
  Core::Threads::ScopedLock guard(lock_);
  if (descriptor_ != -1)
    return 0;
  descriptor_ = services_->openFile(path, O_RDWR | O_NOCTTY | O_NONBLOCK);
  if (descriptor_ == -1) {
    Core::DebugPrintf("UART: unable to open %s\n", path);
    return 0;
  }
  Core::DebugPrintf("UART: open_port %s, %d\n", path, descriptor_);
  if (services_->exclusive(descriptor_, TIOCEXCL) == -1)
    Core::DebugPrintf("can not get exclusive control\n");
  // The original preserves the exact virtual return, not an invented0/1 cast.
  return enableHISpeed(false);
}

int UARTComm::enableHISpeed(bool enabled) {
  Core::Threads::ScopedLock guard(lock_);
  if (descriptor_ == -1) {
    Core::DebugPrintf("UART: Invalid Comm Handle\n");
    return 0;
  }
  // Original tcgetattr failure proceeds with indeterminate stack bytes.
  // Defined zero initialization is an explicit source-port adaptation; it is
  // not a claim of equivalence for arbitrary original prior stack contents.
  termios attributes;
  std::memset(&attributes, 0, sizeof(attributes));
  if (services_->getAttributes(descriptor_, attributes) == -1)
    Core::DebugPrintf("UART: can not get attributes from serial port\n");
  services_->makeRaw(attributes);
  attributes.c_cc[VTIME] = 0;
  attributes.c_cc[VMIN] = 0;
  if (enabled) {
    Core::DebugPrintf("UART: HI-Speed activated\n");
    services_->setSpeed(attributes, B230400);
  } else {
    services_->setSpeed(attributes, B115200);
  }
  attributes.c_cflag |= CLOCAL | CREAD | CS8;
  if (services_->setAttributes(descriptor_, TCSANOW, attributes) < 0)
    Core::DebugPrintf("UART: open_port: error setting attributes\n");
  services_->setFlags(descriptor_, F_SETFL, O_NONBLOCK);
  return 1;
}

unsigned char UARTComm::getNextChar(int timeout) {
  constexpr std::uint64_t sign = std::uint64_t{1} << 63;
  const auto first = services_->rawTicks() / 1000000;
  const auto deadline = static_cast<std::uint64_t>(first) +
                        static_cast<std::uint64_t>(std::int64_t(timeout));
  for (;;) {
    unsigned char value = 0;
    if (services_->readFile(descriptor_, &value, 1) == 1)
      return value;
    const auto now = services_->rawTicks() / 1000000;
    if ((static_cast<std::uint64_t>(now) ^ sign) >= (deadline ^ sign))
      return 0;
  }
}
} // namespace Presonus::Panel
