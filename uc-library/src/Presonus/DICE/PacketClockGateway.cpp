// OPTIONAL PRODUCT ADAPTER; omit from fixture builds, which supply the gateway.
// Upstream has no Core::GetAbsoluteTime. This explicitly named independent
// compatibility gateway delegates the source-preferred POSIX monotonic-ns API.
#if !defined(__linux__)
#error                                                                         \
    "This candidate clock adapter covers Linux/POSIX only; raw units differ on other platforms."
#endif
#include "core/system/coretime.h"
#include "presonus/dice/packet_services.hpp"
namespace presonus::dice {
std::int64_t packetClockRawTicks() { return Core::SystemClock::getTime(); }
} // namespace presonus::dice
