#include "presonus/application/LPCProgrammerGeometry.hpp"
#include <cstring>
namespace Presonus {
int LPCProgrammer::waitAnswerStr(const char *expected, int timeout) {
  if (!waitResponse(timeout))
    return 0;
  return std::strcmp(expected, inputState.response.data()) == 0;
}
int LPCProgrammer::writeStringReply(const char *text, int timeout) {
  writeString(text);
  return waitAnswerStr(text, timeout);
}
int LPCProgrammer::sync() {
  writeChar('?');
  if (!waitAnswerStr("Synchronized", 2000) ||
      !writeStringReply("Synchronized", 2000) || !waitAnswerStr("OK", 2000) ||
      !writeStringReply("10000", 2000) || !waitAnswerStr("OK", 2000) ||
      !writeStringReply("A 0", 2000))
    return 0;
  return waitResult(0, 2000) != 0;
}
} // namespace Presonus
