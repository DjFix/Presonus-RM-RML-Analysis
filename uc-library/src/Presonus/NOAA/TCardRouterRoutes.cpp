#include "core/system/coredebug.h"
#include "presonus/noaa/router.hpp"
namespace Presonus::NOAA {
void TCardRouter::setInputToAvbTxRoute(int, int destination, int input,
                                       int type) {
  if (type == 0) {
    const auto slot = lookupADCSlot(static_cast<unsigned char>(input));
    if (slot != 255)
      addIdleRoute(16, static_cast<unsigned char>(destination), 1, slot);
  } else if (type == 1)
    addIdleRoute(16, static_cast<unsigned char>(destination), 6,
                 static_cast<unsigned char>(input));
}
void TCardRouter::setInputToDanteTxRoute(int, int destination, int input,
                                         int type, int enabled) {
  if (enabled == 0) {
    addIdleRoute(8, static_cast<unsigned char>(destination), 2, 0);
  } else if (type == 0) {
    const auto slot = lookupADCSlot(static_cast<unsigned char>(input));
    if (slot != 255) {
      addIdleRoute(8, static_cast<unsigned char>(destination), 1, slot);
      Core::DebugPrintf("ESA: Add ADC route, dantechannel: %d, adcslot: %d\n",
                        destination, int(slot));
    }
  } else if (type == 1)
    addIdleRoute(8, static_cast<unsigned char>(destination), 6,
                 static_cast<unsigned char>(input));
}
void TCardRouter::setTalkbackToAvbTxRoute(int, int destination, int enabled) {
  if (enabled != 0) {
    const auto slot = lookupADCSlot(36);
    if (slot != 255)
      addIdleRoute(16, static_cast<unsigned char>(destination), 1, slot);
  } else
    addIdleRoute(16, static_cast<unsigned char>(destination), 2, 0);
}
void TCardRouter::set2TrackInputRoute(unsigned char left, unsigned char right) {
  addIdleRoute(4, 40, 6, left);
  addIdleRoute(4, 41, 6, right);
}
void TCardRouter::setGEQToFWRoute(unsigned char slot,
                                  unsigned char destination) {
  if (slot <= 15)
    addIdleRoute(6, destination, 5, slot);
}
void TCardRouter::setMixerMuteInputRoute(unsigned char channel, int muted) {
  addIdleRoute(4, channel, muted != 0 ? 6 : 2, channel);
}
} // namespace Presonus::NOAA
