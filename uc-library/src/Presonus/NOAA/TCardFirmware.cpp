#include "core/system/coredebug.h"
#include "core/system/corethread.h"
#include "presonus/application/ResourceLibrary.hpp"
#include "presonus/dsp/audio_hal.hpp"
#include "presonus/noaa/TCardFPGAUpdater.hpp"
#include "presonus/noaa/card.hpp"
#include "presonus/noaa/programmer.hpp"
#include <stdexcept>

namespace {
// Original commstr pointer and pointed-to bytes are independently ELF-bound.
constexpr const char *commstr = "/dev/ttyS0";
Presonus::Dsp::IAudioHAL &
requiredFirmwareHal(presonus::noaa::CardState &state) {
  if (!state.audioHal ||
      static_cast<const void *>(state.audioHal) != state.opaque5c.value)
    throw std::logic_error("TCard firmware requires a live matching typed HAL");
  return *state.audioHal;
}
presonus::application::FirmwareBundleView
requiredBundle(Presonus::FirmwareBundle *bundle) {
  if (!bundle)
    throw std::logic_error(
        "TCard firmware requires both real firmware bundles");
  return presonus::application::FirmwareBundleView::read(*bundle);
}
void requireImage(presonus::application::FirmwareBundleView view) {
  if (view.size < 0 || (view.size != 0 && !view.image))
    throw std::logic_error(
        "TCard firmware image is outside the source-port domain");
}
} // namespace
namespace Presonus::NOAA {
// Signed32 preserves observed numeric errors; original return declarations,
// receiver provenance, native private layout and ARM ABI remain unresolved.
std::int32_t TCard::eraseFirmware() {
  Core::DebugPrintf("NOAA: %s\n", "eraseFirmware");
  auto &hal = requiredFirmwareHal(state_);
  hal.resetBoard(2, 1);
  Core::Threads::CurrentThread::sleep(200);
  TCardProgrammer programmer(nullptr, nullptr, 0);
  bool opened = programmer.open(commstr) != 0;
  if (opened) {
    state_.observedWord44 = 1;
    programmer.unprotect();
    Core::Threads::CurrentThread::sleep(700);
    hal.resetBoard(2, 2);
    Core::Threads::CurrentThread::sleep(200);
    opened = programmer.open(commstr) != 0;
  }
  if (!opened) {
    Core::DebugPrintf("NOAA: %s\n", "No response ARM");
    programmer.close();
    hal.resetBoard(2, 0);
    Core::Threads::CurrentThread::sleep(200);
    hal.resetBoard(2, 0);
    Core::Threads::CurrentThread::sleep(200);
    return 2008;
  }
  programmer.eraseAll();
  programmer.close();
  Core::Threads::CurrentThread::sleep(200);
  Core::DebugPrintf("NOAA: %s\n", "erased");
  start(true);
  return 0;
}
std::int32_t TCard::updateFirmware(UC::IFirmwareUpdateListener *listener,
                                   int mode) {
  Core::DebugPrintf("NOAA: %s\n", "updateFirmware");
  // Both original getter calls precede mode selection, including mode0.
  auto *armBundle = getArmFirmwareBundle();
  auto *fpgaBundle = getFpgaFirmwareBundle();
  const auto arm = requiredBundle(armBundle);
  const auto fpga = requiredBundle(fpgaBundle);
  bool updated = false;
  if (static_cast<std::uint32_t>(mode) - 1U <= 1U &&
      state_.observedWord20 != arm.version) {
    Core::DebugPrintf("IOCARD: ARM out of date found:0x%x expected:0x%x\n",
                      state_.observedWord20, arm.version);
    requireImage(arm);
    auto &hal = requiredFirmwareHal(state_);
    hal.resetBoard(2, 1);
    Core::Threads::CurrentThread::sleep(200);
    TCardProgrammer programmer(listener, arm.image,
                               static_cast<unsigned int>(arm.size));
    bool opened = programmer.open(commstr) != 0;
    if (opened) {
      state_.observedWord44 = 1;
      programmer.unprotect();
      Core::Threads::CurrentThread::sleep(100);
      hal.resetBoard(2, 2);
      Core::Threads::CurrentThread::sleep(200);
      opened = programmer.open(commstr) != 0;
    }
    if (!opened) {
      Core::DebugPrintf("NOAA: %s\n", "No response from ARM2");
      programmer.close();
      hal.resetBoard(2, 0);
      Core::Threads::CurrentThread::sleep(200);
      return 2008;
    }
    programmer.update();
    programmer.close();
    hal.resetBoard(2, 0);
    Core::Threads::CurrentThread::sleep(200);
    updated = true;
  }
  if ((mode == 1 || mode == 3) && state_.observedWord28 != fpga.version) {
    Core::DebugPrintf("IOCARD: FPGA out of date 0x%x 0x%x\n",
                      state_.observedWord28, fpga.version);
    requireImage(fpga);
    TCardFPGAUpdater updater(listener, fpgaBundle);
    state_.observedWord28 = 0;
    state_.observedWord18 = 0;
    state_.observedWord24 = 0;
    const auto result = updater.update();
    if (result != 0) {
      Core::DebugPrintf("FPGA DFU failed\n");
      return result;
    }
    updated = true;
  }
  if (!updated)
    return 0;
  Core::Threads::CurrentThread::sleep(700);
  if (listener)
    listener->onProgress("restarting card", 0.95f);
  start(true);
  if (listener)
    listener->onProgress("finished", 1.f);
  if (!isMounted()) {
    Core::DebugPrintf("isMounted check after DFU failed\n");
    return 2009;
  }
  if (!isFirmwareCompatible(1)) {
    Core::DebugPrintf("Card check after DFU failed\n");
    return 2009;
  }
  return 0;
}
} // namespace Presonus::NOAA
