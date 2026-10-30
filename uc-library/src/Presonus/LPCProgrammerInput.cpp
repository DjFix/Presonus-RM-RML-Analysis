#include "core/system/coretime.h"
#include "presonus/application/LPCProgrammerGeometry.hpp"
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <unistd.h>
namespace {
Core::int64 milliseconds() {
  // Actual pinned POSIX clock frequency is 1GHz; use its real integer API to
  // avoid introducing a floating conversion at byte timeout boundaries.
  return Core::SystemClock::getTime() /
         static_cast<Core::int64>(Core::SystemClock::getFrequency() / 1000);
}
} // namespace
namespace Presonus {
int LPCProgrammer::getNextChar(int timeout) {
  const std::uint64_t deadlineBits =
      static_cast<std::uint64_t>(milliseconds()) +
      static_cast<std::uint64_t>(static_cast<std::int64_t>(timeout));
  std::int64_t deadline;
  std::memcpy(&deadline, &deadlineBits, sizeof deadline);
  for (;;) {
    unsigned char value = 0;
    if (::read(inputState.descriptor, &value, 1) == 1)
      return value;
    if (milliseconds() >= deadline)
      return 0;
  }
}
int LPCProgrammer::waitResponse(int timeout) {
  auto &buffer = inputState.response;
  buffer[0] = 0;
  unsigned count = 0;
  for (;;) {
    const int value = getNextChar(timeout);
    if (value == 10 || value == 0)
      break;
    if (value == 13)
      continue;
    buffer[count++] = static_cast<char>(value);
    buffer[count] = 0;
    if (count == 128)
      break;
  }
  return count != 0;
}
int LPCProgrammer::waitResult(int expected, int timeout) {
  if (!waitResponse(timeout))
    return 0;
  // Original ARM32 strtol saturates to signed32. Modern Linux long is64;
  // preserve that original range/ERANGE while using the actual libc parser.
  const long long parsed =
      std::strtoll(inputState.response.data(), nullptr, 10);
  std::int32_t value;
  if (parsed > std::numeric_limits<std::int32_t>::max()) {
    errno = ERANGE;
    value = std::numeric_limits<std::int32_t>::max();
  } else if (parsed < std::numeric_limits<std::int32_t>::min()) {
    errno = ERANGE;
    value = std::numeric_limits<std::int32_t>::min();
  } else {
    value = static_cast<std::int32_t>(parsed);
  }
  return value == expected;
}
} // namespace Presonus
