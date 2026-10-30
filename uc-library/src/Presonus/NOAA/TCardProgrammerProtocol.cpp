#include "core/public/corestringbuffer.h"
#include "presonus/noaa/programmer.hpp"
#include <cstring>
// Original global identity: zero-initialized NOBITS, milliseconds.
static std::int64_t gStartTicks;
namespace {
std::int64_t deadline(std::int64_t first, int timeout) {
  const auto bits =
      static_cast<std::uint64_t>(first) +
      static_cast<std::uint64_t>(static_cast<std::int64_t>(timeout));
  std::int64_t value;
  std::memcpy(&value, &bits, sizeof value);
  return value;
}
std::int64_t elapsed(std::int64_t now, std::int64_t start) {
  const auto bits =
      static_cast<std::uint64_t>(now) - static_cast<std::uint64_t>(start);
  std::int64_t value;
  std::memcpy(&value, &bits, sizeof value);
  return value;
}
} // namespace
namespace presonus::noaa {
void setProgrammerProgressEpochMilliseconds(std::int64_t value) {
  gStartTicks = value;
}
} // namespace presonus::noaa
namespace Presonus::NOAA {
void TCardProgrammer::printProgress(const char *message, bool emit) {
  auto &services =
      receive_ ? *receive_ : presonus::noaa::posixProgrammerReceiveServices();
  if (state_.listener) {
    const auto milliseconds = services.clockRawTicks() / 1000000;
    const float progress =
        static_cast<float>(elapsed(milliseconds, gStartTicks)) / 34000.0f;
    state_.listener->onProgress(message, progress);
  }
  if (emit) {
    services.debugMessage(message);
    services.debugMessage("\n");
  }
}
std::int32_t TCardProgrammer::getNextChar(int timeout) {
  auto &services =
      receive_ ? *receive_ : presonus::noaa::posixProgrammerReceiveServices();
  const auto until = deadline(services.clockRawTicks() / 1000000, timeout);
  while (true) {
    unsigned char byte = 0;
    if (services.readByte(state_.descriptor, &byte) == 1)
      return byte;
    if (until <= services.clockRawTicks() / 1000000) {
      printProgress("IOCARD: getNextChar timeout", true);
      return 0;
    }
  }
}
std::int32_t TCardProgrammer::waitAck(int timeout) {
  return getNextChar(timeout) == 0x79 ? 1 : 0;
}
std::int32_t TCardProgrammer::sync() {
  writeChar(0x7f);
  return waitAck(2000);
}
std::int32_t TCardProgrammer::doCommand(unsigned char command) {
  writeChar(command);
  writeChar(static_cast<unsigned char>(~command));
  if (waitAck(2000))
    return 1;
  Core::CString128 message;
  message.appendFormat("IOCARD: CMD Err %d", static_cast<int>(command));
  printProgress(message.getBuffer(), true);
  return 0;
}
} // namespace Presonus::NOAA
