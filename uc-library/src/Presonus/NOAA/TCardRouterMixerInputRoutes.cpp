#include "core/system/coredebug.h"
#include "presonus/noaa/router.hpp"
#include <cstdint>
namespace {
unsigned char byte(std::uint32_t value) {
  return static_cast<unsigned char>(value);
}
} // namespace
namespace Presonus::NOAA {
void TCardRouter::setAvbToSlaveFwRecordRoute(int bus, int source, int count,
                                             bool enabled) {
  if (!enabled) {
    for (unsigned int channel = 0; channel < 22; ++channel)
      addIdleRoute(7, byte(channel), 0, byte(channel + 42));
    return;
  }
  if (count <= 0)
    return;
  const auto device = byte(static_cast<std::uint32_t>(bus) + 16u);
  auto input = static_cast<std::uint32_t>(source);
  for (std::uint32_t channel = 0; channel < static_cast<std::uint32_t>(count);
       ++channel, ++input)
    addIdleRoute(7, byte(channel), device, byte(input));
}
void TCardRouter::setAvbTapeRxToDigitalReturnRoute(int bus, int source,
                                                   bool enabled) {
  if (!enabled) {
    addIdleRoute(4, 40, 2, 0);
    addIdleRoute(4, 41, 2, 0);
    return;
  }
  const auto device = byte(static_cast<std::uint32_t>(bus) + 16u);
  const auto input = static_cast<std::uint32_t>(source);
  addIdleRoute(4, 40, device, byte(input));
  addIdleRoute(4, 41, device, byte(input + 1u));
}
void TCardRouter::setMixerInputRoute(unsigned char channel, int mode,
                                     bool queued) {
  if (channel > 39)
    return;
  if (mode == 2) {
    addIdleRoute(4, channel, 16, channel);
    Core::DebugPrintf("MixerInputRoute AVB:%d %d\n", int(channel),
                      int(channel));
    return;
  }
  if (mode == 3) {
    addIdleRoute(4, channel, 8, channel);
    return;
  }
  unsigned char device = 6, input = channel;
  if (mode != 1) {
    const auto slot = lookupADCSlot(channel);
    device = slot == 255 ? 2 : 1;
    if (slot != 255)
      input = slot;
  }
  if (queued)
    addIdleRoute(4, channel, device, input);
  else
    doRouteCommand(4, channel, device, input, 1);
}
} // namespace Presonus::NOAA
