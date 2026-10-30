#include "presonus/dice/response_wait_detail.hpp"
#include "presonus/dice/sysex.hpp"
namespace Presonus::DICE {
unsigned char SysexReceiver::waitAck(long long timeout) {
  return presonus::dice::detail::waitAck(state_, *responseServices_, timeout,
                                         false, portableStateLock_);
}
bool SysexReceiver::waitResponseSet(unsigned int &response, long long timeout) {
  return presonus::dice::detail::waitResponseSet(
      response, *responseServices_, timeout, false, portableStateLock_);
}
} // namespace Presonus::DICE
