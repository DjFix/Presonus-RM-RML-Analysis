#include "presonus/dice/response_wait_detail.hpp"
#include "presonus/noaa/sysex_receiver.hpp"

namespace Presonus::NOAA {
unsigned char SysexReceiver::waitAck(long long timeout) {
  return presonus::dice::detail::waitAck(state_, *services_, timeout, true);
}
bool SysexReceiver::waitResponseSet(unsigned int &response, long long timeout) {
  return presonus::dice::detail::waitResponseSet(response, *services_, timeout,
                                                 true);
}
} // namespace Presonus::NOAA
