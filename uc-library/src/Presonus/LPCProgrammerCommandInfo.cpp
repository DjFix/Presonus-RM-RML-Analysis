#include "presonus/application/LPCProgrammerGeometry.hpp"
#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <unistd.h>
namespace {
// Same explicit ARM32 libc-range adaptation as the frozen input profile.
// Real libc parses prefixes; original ordinary return declarations stay
// pending.
std::int32_t responseValue32(const char *text) {
  const long long value = std::strtoll(text, nullptr, 10);
  if (value > std::numeric_limits<std::int32_t>::max()) {
    errno = ERANGE;
    return std::numeric_limits<std::int32_t>::max();
  }
  if (value < std::numeric_limits<std::int32_t>::min()) {
    errno = ERANGE;
    return std::numeric_limits<std::int32_t>::min();
  }
  return static_cast<std::int32_t>(value);
}
} // namespace
namespace Presonus {
int LPCProgrammer::writeString(const char *text) {
  // Original ignores the first write result and always attempts CRLF.
  (void)::write(inputState.descriptor, text, std::strlen(text));
  return static_cast<int>(::write(inputState.descriptor, "\r\n", 2));
}
int LPCProgrammer::waitValue(const char *command, int) {
  // Encoded timeout parameter is unused by the original body.
  writeString(command);
  if (!waitResult(0, 2000) || !waitResponse(2000))
    return -1;
  return responseValue32(inputState.response.data());
}
int LPCProgrammer::readInfo() {
  imageState.raw18 = static_cast<std::uint32_t>(waitValue("J", 2000));
  deviceIdentity.raw2c = static_cast<std::uint32_t>(waitValue("K", 2000));
  writeString("N");
  (void)waitResult(0, 2000);
  if (!waitResult(0, 2000))
    return 0;
  for (auto &word : deviceIdentity.raw1c_to28) {
    if (!waitResponse(2000))
      return 0;
    word =
        static_cast<std::uint32_t>(responseValue32(inputState.response.data()));
  }
  return 1;
}
} // namespace Presonus
