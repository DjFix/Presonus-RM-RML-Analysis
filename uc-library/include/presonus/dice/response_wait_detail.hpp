#pragma once
#include "presonus/dice/packet_services.hpp"
#include "presonus/dice/response_services.hpp"

namespace Core::Threads {
class Lock;
}

namespace presonus::dice::detail {
// Independent shared source-port algorithm; original member scopes remain
// separately defined for DICE and NOAA. NOAA alone has the one-shot forced
// pump.
unsigned char waitAck(SubsystemState &state, ResponseServices &services,
                      long long timeout, bool noaa,
                      Core::Threads::Lock *stateLock = nullptr);
bool waitResponseSet(unsigned int &response, ResponseServices &services,
                     long long timeout, bool noaa,
                     Core::Threads::Lock *stateLock = nullptr);
} // namespace presonus::dice::detail
