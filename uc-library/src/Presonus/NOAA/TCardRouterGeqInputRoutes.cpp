#include "presonus/noaa/router.hpp"
#include <cstdint>
#include <stdexcept>
namespace {
static_assert(sizeof(unsigned int) == sizeof(std::uint32_t));
static_assert(sizeof(int) == sizeof(std::uint32_t));
unsigned char byte(std::uint32_t value) {
  return static_cast<unsigned char>(value);
}
std::int64_t signedBits(std::uint32_t value) {
  return value < 0x80000000u ? std::int64_t(value)
                             : std::int64_t(value) - 0x100000000ll;
}
// Independent shared source-port helper, not an invented original method.
void emitGeq(Presonus::NOAA::TCardRouter &router, unsigned char slot,
             unsigned char channel, unsigned char dac, unsigned int enabled) {
  if (enabled) {
    router.addIdleRoute(5, slot, 3, channel);
    router.addIdleRoute(1, dac, 5, slot);
  } else
    router.addIdleRoute(1, dac, 3, channel);
}
} // namespace
namespace Presonus::NOAA {
void TCardRouter::setGEQTDMSlotInsert(unsigned int slot, unsigned int channel,
                                      unsigned int enabled) {
  if (slot > 15)
    return;
  // Encoded j parameter is retained; original explicitly masks channel to8bits.
  const auto input = byte(channel);
  const auto dac = lookupDACSlot(input);
  if (dac != 255)
    emitGeq(*this, byte(slot), input, dac, enabled);
}
void TCardRouter::setGEQInsert(unsigned int slot, unsigned int enabled) {
  if (slot > 15)
    return;
  if (!state_.slotTables)
    throw std::invalid_argument("Router requires immutable slot tables");
  const auto input = state_.slotTables->geqBytes()[slot];
  const auto dac = lookupDACSlot(input);
  if (dac != 255)
    emitGeq(*this, byte(slot), input, dac, enabled);
}
void TCardRouter::setAvbToDacBypassRoute(int channel, int bus, int source,
                                         int count, bool enabled) {
  auto current = static_cast<std::uint32_t>(channel);
  const auto end = current + static_cast<std::uint32_t>(count);
  auto input = static_cast<std::uint32_t>(source);
  const auto device = byte(static_cast<std::uint32_t>(bus) + 16u);
  while (signedBits(current) < signedBits(end)) {
    const auto destination = byte(current);
    const auto dac = lookupDACSlot(destination);
    if (dac != 255) {
      if (enabled) {
        addIdleRoute(1, dac, device, byte(input));
        ++input;
      } else {
        addIdleRoute(1, dac, 3, destination);
        const auto slot = lookupGeqSlot(destination);
        if (slot != 255)
          setGEQInsert(slot, 1);
      }
    }
    ++current;
  }
}
void TCardRouter::setMixerCustomInputRoute(unsigned char source,
                                           unsigned char destination, int mode,
                                           int bus) {
  if (destination > 41 || source > 39) {
    if (source == 255)
      addIdleRoute(4, destination, 2, 0);
    return;
  }
  if (mode == 0) {
    const auto slot = lookupADCSlot(source);
    addIdleRoute(4, destination, slot == 255 ? 2 : 1,
                 slot == 255 ? destination : slot);
  } else if (mode == 2)
    addIdleRoute(4, destination, byte(static_cast<std::uint32_t>(bus) + 16u),
                 source);
  else
    addIdleRoute(4, destination, mode == 3 ? 8 : 6, source);
}
void TCardRouter::setSPDIFRoute(unsigned char left, unsigned char right,
                                int mode) {
  unsigned char leftInput = left, rightInput = right, device;
  if (mode == 0) {
    leftInput = lookupADCSlot(left);
    rightInput = lookupADCSlot(right);
    if (leftInput == 255 || rightInput == 255)
      return;
    device = 1;
  } else
    device = mode == 1 ? 6 : 3;
  addIdleRoute(2, 0, device, leftInput);
  addIdleRoute(2, 1, device, rightInput);
}
void TCardRouter::setAVS48Route(unsigned char destination, unsigned char source,
                                int mode, unsigned char bus) {
  if (destination > 52)
    return;
  if (mode == 0) {
    const auto slot = lookupADCSlot(source);
    addIdleRoute(6, destination, slot == 255 ? 2 : 1,
                 slot == 255 ? destination : slot);
  } else if (mode == 1)
    addIdleRoute(6, destination, 6, source);
  else if (mode == 4)
    addIdleRoute(6, destination, 3, source);
  else if (mode == 2)
    addIdleRoute(6, destination, byte(std::uint32_t(bus) + 16u), source);
}
} // namespace Presonus::NOAA
