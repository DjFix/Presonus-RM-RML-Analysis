#include "core/system/coredebug.h"
#include "presonus/dsp/audio_hal.hpp"
#include "presonus/noaa/card.hpp"
#include <stdexcept>
namespace {
Presonus::Dsp::IAudioHAL &requiredHal(presonus::noaa::CardState &state) {
  if (!state.audioHal ||
      static_cast<const void *>(state.audioHal) != state.opaque5c.value)
    throw std::logic_error(
        "TCard reset requires a live matching typed audio HAL binding");
  return *state.audioHal;
}
} // namespace
namespace Presonus::NOAA {
bool TCard::start(bool force) {
  Core::DebugPrintf("NOAA: %s\n", "start");
  TCardSPI::instance().onIdle(true);
  if (!force && state_.observedWord18 != 0) {
    sendSampleRate(1, 0);
    waitResponseSet(state_.observedWord40, 3000);
  } else {
    state_.observedWord1c = 0;
    state_.observedWord24 = 0;
    state_.observedWord20 = 0;
    state_.observedWord28 = 0;
    state_.observedWord40 = 0;
    state_.observedWord34 = 0;
    state_.observedWord38 = 0;
    state_.observedWord3c = 0;
    requiredHal(state_).resetBoard(2, 0);
    waitResponseSet(state_.observedWord20, 6000);
    if (!isMounted()) {
      printStatus();
      Core::DebugPrintf("NOAA: %s\n", "did not start");
      return false;
    }
    if (state_.observedWord18 != 0) {
      sendSampleRate(1, 0);
      waitResponseSet(state_.observedWord40, 3000);
    }
  }
  printStatus();
  const unsigned char bytes[] = {0xf0, 0x22, 1, 0xf7};
  SysexPacket packet(bytes, 4);
  post(packet);
  waitAck(500);
  return state_.observedWord18 != 0;
}
} // namespace Presonus::NOAA
