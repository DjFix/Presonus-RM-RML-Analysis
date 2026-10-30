#include "presonus/noaa/router.hpp"
#include <cstdint>
namespace {
static_assert(sizeof(int) == sizeof(std::uint32_t));
std::int64_t signedBits(std::uint32_t bits) {
  return bits < 0x80000000u ? std::int64_t(bits)
                            : std::int64_t(bits) - 0x100000000ll;
}
unsigned char byte(std::uint32_t bits) {
  return static_cast<unsigned char>(bits);
}
} // namespace
namespace Presonus::NOAA {
void TCardRouter::setAvbToLinkBusRoute(int bus, int source, int destination,
                                       int count) {
  auto current = static_cast<std::uint32_t>(destination);
  const auto end = current + static_cast<std::uint32_t>(count);
  auto input = static_cast<std::uint32_t>(source);
  const auto device = byte(static_cast<std::uint32_t>(bus) + 16u);
  while (signedBits(current) < signedBits(end)) {
    const auto channel = byte(current);
    addIdleRoute(4, channel, device, byte(input));
    addIdleRoute(0, channel, 4, channel);
    ++current;
    ++input;
  }
}
void TCardRouter::setLinkBusToAvbRoute(int, int destination, int source,
                                       int count) {
  auto current = static_cast<std::uint32_t>(source);
  const auto end = current + static_cast<std::uint32_t>(count);
  auto output = static_cast<std::uint32_t>(destination);
  while (signedBits(current) < signedBits(end)) {
    addIdleRoute(16, byte(output), 7, byte(current));
    ++current;
    ++output;
  }
}
void TCardRouter::setDspToDanteTxRoute(int bus, int destination, int source,
                                       int count) {
  if (count < 0)
    return;
  const auto device = byte(static_cast<std::uint32_t>(bus) + 8u);
  auto output = byte(static_cast<std::uint32_t>(destination));
  auto current = static_cast<std::uint32_t>(source);
  if (count == 0) {
    addIdleRoute(device, output, 2, byte(current));
    return;
  }
  const auto end = current + static_cast<std::uint32_t>(count);
  do {
    unsigned char slot = 255;
    if (current == 60u || current - 42u <= 11u || current == 61u ||
        current == 58u)
      slot = lookupGeqSlot(byte(current));
    addIdleRoute(device, output, slot == 255 ? 3 : 5,
                 slot == 255 ? byte(current) : slot);
    ++current;
    output = byte(std::uint32_t(output) + 1u);
  } while (current != end);
}
void TCardRouter::setDspToAvbTxRoute(int bus, int destination, int source,
                                     int count, bool muted) {
  if (destination < 0 || count < 0)
    return;
  const auto device = byte(static_cast<std::uint32_t>(bus) + 16u);
  auto output = byte(static_cast<std::uint32_t>(destination));
  auto input = byte(static_cast<std::uint32_t>(source));
  if (count == 0) {
    addIdleRoute(device, output, 2, input);
    return;
  }
  // Faithful original uint8 counter versus raw signed count. Counts>=256 do
  // not terminate; no count cap or firmware bug fix is introduced here.
  unsigned char iteration = 0;
  do {
    const auto slot = lookupGeqSlot(input);
    addIdleRoute(device, output, muted ? 2 : (slot == 255 ? 3 : 5),
                 slot == 255 ? input : slot);
    iteration = byte(std::uint32_t(iteration) + 1u);
    output = byte(std::uint32_t(output) + 1u);
    input = byte(std::uint32_t(input) + 1u);
  } while (int(iteration) < count);
}
void TCardRouter::setAvbTapeLRToAvbTxRoute(int, int destination, int enabled) {
  const auto output = byte(static_cast<std::uint32_t>(destination));
  if (!enabled) {
    addIdleRoute(16, output, 2, 0);
    addIdleRoute(16, byte(std::uint32_t(output) + 1u), 2, 0);
    return;
  }
  const auto left = lookupADCSlot(38);
  if (left == 255)
    return;
  addIdleRoute(16, output, 1, left);
  addIdleRoute(16, byte(std::uint32_t(output) + 1u), 1, lookupADCSlot(39));
}
void TCardRouter::setAvbStageBoxMainRoute(int bus, int source, int enabled) {
  const auto device = byte(static_cast<std::uint32_t>(bus) + 16u);
  auto input = byte(static_cast<std::uint32_t>(source));
  for (const auto channel : {60, 61, 58}) {
    const auto slot = lookupDACSlot(static_cast<unsigned char>(channel));
    addIdleRoute(1, slot, enabled ? device : 3,
                 enabled ? input : static_cast<unsigned char>(channel));
    input = byte(std::uint32_t(input) + 1u);
  }
}
} // namespace Presonus::NOAA
