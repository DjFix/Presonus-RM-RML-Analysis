#include "core/system/coredebug.h"
#include "core/system/coretime.h"
#include "presonus/noaa/programmer.hpp"
#include <cstring>
#include <unistd.h>
namespace presonus::noaa {
namespace {
class PosixReceiveServices final : public ProgrammerReceiveServices {
public:
  std::int64_t clockRawTicks() override { return Core::SystemClock::getTime(); }
  std::int32_t readByte(std::int32_t fd, unsigned char *byte) override {
    return static_cast<std::int32_t>(::read(fd, byte, 1));
  }
  void debugMessage(const char *message) override {
    Core::DebugPrintf(message);
  }
  void responseTimeout() override {
    Core::DebugPrintf("waitResponse timeout. \n");
  }
  void responseReadError(std::int32_t value) override {
    Core::DebugPrintf("NOAA waitResponse read err : %d. \n", value);
  }
};
} // namespace
ProgrammerReceiveServices &posixProgrammerReceiveServices() {
  static PosixReceiveServices services;
  return services;
}
} // namespace presonus::noaa
namespace Presonus::NOAA {
std::int32_t TCardProgrammer::waitResponse(int timeout) {
  auto &services =
      receive_ ? *receive_ : presonus::noaa::posixProgrammerReceiveServices();
  std::memset(state_.response.data(), 0, 128);
  const auto first = services.clockRawTicks() / 1000000;
  const auto bits =
      static_cast<std::uint64_t>(first) +
      static_cast<std::uint64_t>(static_cast<std::int64_t>(timeout));
  std::int64_t deadline;
  std::memcpy(&deadline, &bits, sizeof deadline);
  std::uint32_t count = 0;
  unsigned char byte = 0;
  while (true) {
    if (deadline <= services.clockRawTicks() / 1000000) {
      services.responseTimeout();
      return -1;
    }
    const auto result = services.readByte(state_.descriptor, &byte);
    if (result < 0) {
      services.responseReadError(result);
      return result;
    }
    if (result == 1) {
      state_.response[count + 1] = 0;
      state_.response[count] = byte;
      ++count;
      if (byte == 0x79 || count == 128)
        return static_cast<std::int32_t>(count);
    }
  }
}
} // namespace Presonus::NOAA
