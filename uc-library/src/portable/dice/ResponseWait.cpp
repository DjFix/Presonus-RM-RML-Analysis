#include "ReceiverStateGuard.hpp"
#include "presonus/dice/response_wait_detail.hpp"
#include <cstdint>
#include <cstring>

namespace {
std::int64_t wrappedDifference(std::int64_t current, std::int64_t start) {
  const auto bits =
      static_cast<std::uint64_t>(current) - static_cast<std::uint64_t>(start);
  std::int64_t result;
  std::memcpy(&result, &bits, sizeof result);
  return result;
}
unsigned char readCommand(const presonus::dice::SubsystemState &state,
                          Core::Threads::Lock *lock) {
  presonus::dice::ReceiverStateGuard guard(lock);
  return state.command;
}
unsigned int readResponse(const unsigned int &response,
                          Core::Threads::Lock *lock) {
  presonus::dice::ReceiverStateGuard guard(lock);
  return response;
}
} // namespace

namespace presonus::dice::detail {
unsigned char waitAck(SubsystemState &state, ResponseServices &services,
                      long long timeout, bool noaa,
                      Core::Threads::Lock *stateLock) {
  const std::int64_t start = services.clockRawTicks() / 1000000;
  bool forced = false;
  while (readCommand(state, stateLock) == 0) {
    services.pumpIdle(false);
    services.sleepMilliseconds(1);
    const std::int64_t current = services.clockRawTicks() / 1000000;
    const auto elapsed = wrappedDifference(current, start);
    if (elapsed > timeout) {
      services.timeoutNotice(false, 0, 0);
      return readCommand(state, stateLock);
    }
    if (noaa && !forced && elapsed > 60) {
      services.pumpIdle(true);
      forced = true;
    }
  }
  return readCommand(state, stateLock);
}

bool waitResponseSet(unsigned int &response, ResponseServices &services,
                     long long timeout, bool noaa,
                     Core::Threads::Lock *stateLock) {
  static_assert(sizeof(unsigned int) == 4);
  {
    presonus::dice::ReceiverStateGuard guard(stateLock);
    response = 0;
  }
  const std::int64_t start = services.clockRawTicks() / 1000000;
  bool forced = false;
  while (readResponse(response, stateLock) == 0) {
    services.pumpIdle(false);
    services.sleepMilliseconds(1);
    const std::int64_t current = services.clockRawTicks() / 1000000;
    const auto elapsed = wrappedDifference(current, start);
    if (elapsed > timeout) {
      if (readResponse(response, stateLock) == 0)
        services.timeoutNotice(true, 0, static_cast<std::uint32_t>(timeout));
      return readResponse(response, stateLock) != 0;
    }
    if (noaa && !forced && elapsed > 23) {
      services.pumpIdle(true);
      forced = true;
    }
  }
  return readResponse(response, stateLock) != 0;
}
} // namespace presonus::dice::detail
