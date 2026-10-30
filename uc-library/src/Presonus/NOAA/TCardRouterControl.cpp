#include "../../portable/noaa/RouterHelpers.hpp"
#include "core/system/coredebug.h"
#include "presonus/noaa/router.hpp"
#include <algorithm>
#include <cstdint>
#include <stdexcept>

namespace {
constexpr std::size_t flagOffset = 0x118 - 0x18;
constexpr std::size_t countOffset = 0x11c - 0x18;
constexpr std::size_t routesOffset = 0x120 - 0x18;
std::uint32_t loadCount(const presonus::noaa::RouterState &state) {
  const auto &bytes = state.applicationBytes;
  std::uint32_t word = 0;
  for (unsigned i = 0; i < 4; ++i)
    word |= std::uint32_t(bytes[countOffset + i]) << (8 * i);
  return word;
}
void storeCount(presonus::noaa::RouterState &state, std::uint32_t word) {
  for (unsigned i = 0; i < 4; ++i)
    state.applicationBytes[countOffset + i] =
        static_cast<unsigned char>(word >> (8 * i));
}
std::int64_t signedWord(std::uint32_t word) {
  return word < 0x80000000u ? static_cast<std::int64_t>(word)
                            : static_cast<std::int64_t>(word) - 0x100000000ll;
}
} // namespace

namespace Presonus::NOAA {
bool TCardRouter::addIdleRoute(unsigned char device0, unsigned char channel0,
                               unsigned char device1, unsigned char channel1) {
  Core::Threads::ScopedLock guard(state_.lock);
  // Original loads only after acquiring its lock; no cached pre-lock value.
  const auto bits = loadCount(state_);
  if (signedWord(bits) >= 512) {
    Core::DebugPrintf("!!!!!!!!!!!!!!! missed Route\n");
    return false;
  }
  // Original unsigned32 ADD/LSL wrap is observable even for INT_MIN/-2^30.
  const std::uint32_t destination = (bits + 0x48u) << 2;
  if (destination < 0x18 || destination > 0x91c)
    throw std::out_of_range("Router queued route leaves application byte span");
  storeCount(state_, bits + 1u);
  auto &bytes = state_.applicationBytes;
  bytes[flagOffset] = 1;
  const auto index = static_cast<std::size_t>(destination - 0x18);
  // Preserve original store order. For count=-1 the route overwrites the
  // incremented count word; do not re-store or normalize that aliased result.
  bytes[index] = device0;
  bytes[index + 3] = channel1;
  bytes[index + 1] = channel0;
  bytes[index + 2] = device1;
  return true;
}
void TCardRouter::idle() {
  // Original fast flag read precedes lock. Existing setup/calls remain caller-
  // serialized; this preserves the bounded branch without claiming a new
  // concurrent raw-state API or original Core synchronization semantics.
  if (state_.applicationBytes[flagOffset] == 0)
    return;
  Core::Threads::ScopedLock guard(state_.lock);
  auto remaining = signedWord(loadCount(state_));
  // Independent guard: original queue index512 first reads its Core member.
  if (remaining > 512)
    throw std::out_of_range("Router idle input reaches original Core region");
  state_.applicationBytes[flagOffset] = 0;
  storeCount(state_, 0);
  std::size_t processed = 0;
  while (remaining > 0) {
    const auto count = static_cast<int>(std::min<std::int64_t>(remaining, 59));
    auto *routes = reinterpret_cast<DiceRoute *>(
        state_.applicationBytes.data() + routesOffset + 4 * processed);
    // The actual CCL source lock stays held across post/ack exactly as the
    // original caller boundary. No old Core implementation is reconstructed.
    doRouteCommands(routes, count, 1);
    processed += static_cast<std::size_t>(count);
    remaining -= count;
  }
}
void TCardRouter::doRouteCommand(unsigned char device0, unsigned char channel0,
                                 unsigned char device1, unsigned char channel1,
                                 unsigned char remap) {
  if (remap) {
    if (device0 == 0)
      channel0 = presonus::noaa::mapRouterChannel(channel0, lookup_);
    if (device1 == 0)
      channel1 = presonus::noaa::mapRouterChannel(channel1, lookup_);
  }
  // Unlike bulk routing, this original method deliberately does NOT mask7bits
  // and does NOT touch the application command-byte storage.
  const unsigned char data[]{0xf0,    0x16,     device0, channel0,
                             device1, channel1, 0xf7};
  SysexPacket packet(data, 7);
  post(packet);
  if (!waitAck(500) || !portableState().status)
    Core::DebugPrintf(
        "NOAA:route err found. destID:%d destch:%d srcID:%d srcch:%d\n",
        device0, channel0, device1, channel1);
}
} // namespace Presonus::NOAA
