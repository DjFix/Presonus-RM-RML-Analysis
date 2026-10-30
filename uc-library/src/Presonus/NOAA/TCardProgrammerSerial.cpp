#include "core/system/coredebug.h"
#include "presonus/noaa/programmer.hpp"
#include <cerrno>
#include <cstring>
#include <fcntl.h>
namespace presonus::noaa {
namespace {
class PosixSerialServices final : public ProgrammerSerialServices {
public:
  std::int32_t openPath(const char *path, int flags) override {
    return ::open(path, flags);
  }
  int getAttributes(int fd, termios &value) override {
    return ::tcgetattr(fd, &value);
  }
  int flushInput(int fd) override { return ::tcflush(fd, TCIFLUSH); }
  int setAttributes(int fd, const termios &value) override {
    return ::tcsetattr(fd, TCSANOW, &value);
  }
  int lastError() override { return errno; }
  void openError(const char *path, int error) override {
    Core::DebugPrintf("Can't open COM-Port %s ! (Error: %dd (0x%X))\n", path,
                      error, static_cast<unsigned int>(error));
  }
};
} // namespace
ProgrammerSerialServices &posixProgrammerSerialServices() {
  static PosixSerialServices services;
  return services;
}
} // namespace presonus::noaa
namespace Presonus::NOAA {
std::int32_t TCardProgrammer::openPort(const char *path) {
  if (state_.descriptor != -1)
    return 1;
  auto &services =
      serial_ ? *serial_ : presonus::noaa::posixProgrammerSerialServices();
  static_assert((O_RDWR | O_NOCTTY | O_NONBLOCK) == 0x902,
                "Linuxflagdomain differs fromoriginal app");
  state_.descriptor = services.openPath(path, O_RDWR | O_NOCTTY | O_NONBLOCK);
  if (state_.descriptor < 0) {
    const auto error = services.lastError();
    services.openError(path, error);
    return 0;
  }
  termios discarded{};
  services.getAttributes(state_.descriptor, discarded);
  termios settings;
  std::memset(&settings, 0, sizeof settings);
  static_assert((INPCK | ISTRIP) == 0x30 &&
                    (B115200 | CS8 | CLOCAL | CREAD | PARENB) == 0x19b2,
                "Linuxtermiosflagdomain differs");
  settings.c_iflag = INPCK | ISTRIP;
  settings.c_cflag = B115200 | CS8 | CLOCAL | CREAD | PARENB;
  settings.c_cc[VTIME] = 0;
  settings.c_cc[VMIN] = 0;
  services.flushInput(state_.descriptor);
  if (services.setAttributes(state_.descriptor, settings) == 0)
    return 1;
  printProgress("IOCARD: serial open Err.", true);
  return 0;
}
std::int32_t TCardProgrammer::open(const char *path) {
  if (!openPort(path)) {
    printProgress("IOCARD: port err", true);
    return 0;
  }
  if (!sync()) {
    printProgress("IOCARD: sync err", true);
    return 0;
  }
  if (!readInfo()) {
    printProgress("IOCARD: readinfo err", true);
    return 0;
  }
  printInfo();
  return 1;
}
} // namespace Presonus::NOAA
