#include "core/system/coredebug.h"
#include "presonus/noaa/diagnostics.hpp"
#include "presonus/noaa/router.hpp"
#include <array>
#include <cstdint>

// Original internal global identity and96bytes. uint32_t element declaration is
// a portable source choice; only original firstbyte loads atstride4 are proven.
[[gnu::used]] static const std::uint32_t gTDMOutputSlots[24] = {
    42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53,
    54, 55, 38, 39, 40, 41, 60, 61, 56, 57, 58, 59};

void printNOAA(const char *message) {
  if (message[0])
    Core::DebugPrintf("NOAA: %s\n", message);
}

namespace Presonus::NOAA {
void TCardRouter::routeAnalogIns(bool muted) {
  std::array<DiceRoute, 42> routes{};
  for (unsigned int channel = 0; channel < 40; ++channel) {
    unsigned char device = 2, input = static_cast<unsigned char>(channel);
    if (!muted) {
      const auto slot = lookupADCSlot(static_cast<unsigned char>(channel));
      if (slot != 255) {
        device = 1;
        input = slot;
      }
    }
    routes[channel] = {{4, static_cast<unsigned char>(channel), device, input}};
  }
  doRouteCommands(routes.data(), 40, 1);
  if (!muted)
    for (unsigned char channel = 0; channel < 32; ++channel)
      setAVS48Route(channel, channel, 4, 0);
}
void TCardRouter::initRoutes() {
  printNOAA("initRoutes start");
  std::array<DiceRoute, 64> routes{};
  for (unsigned int channel = 0; channel < 64; ++channel)
    routes[channel] = {{0, static_cast<unsigned char>(channel), 4,
                        static_cast<unsigned char>(channel)}};
  doRouteCommands(routes.data(), 60, 1);
  doRouteCommands(routes.data() + 60, 4, 1);
  for (unsigned int channel = 0; channel < 64; ++channel)
    routes[channel] = {{3, static_cast<unsigned char>(channel), 0,
                        static_cast<unsigned char>(channel)}};
  doRouteCommands(routes.data(), 60, 1);
  doRouteCommands(routes.data() + 60, 4, 1);
  unsigned int matched = 0;
  for (auto raw : gTDMOutputSlots) {
    const auto channel = static_cast<unsigned char>(raw);
    const auto slot = lookupDACSlot(channel);
    if (slot != 255)
      routes[matched++] = {{1, slot, 3, channel}};
  }
  doRouteCommands(routes.data(), static_cast<int>(matched), 1);
  for (unsigned int slot = 0; slot < 16; ++slot)
    setGEQInsert(slot, 1);
  routeAnalogIns(false);
  for (unsigned int channel = 0; channel < 22; ++channel)
    routes[channel] = {{7, static_cast<unsigned char>(channel), 0,
                        static_cast<unsigned char>(channel + 42)}};
  doRouteCommands(routes.data(), 22, 1);
  printNOAA("initRoutes done");
}
} // namespace Presonus::NOAA
