#include "core/system/coredebug.h"
#include "presonus/dice/packet_services.hpp"
#include "presonus/panel/PanelRegistrar.hpp"
#include "presonus/panel/RackPanelComponent.hpp"
namespace Presonus::Panel {
void RackPanelComponent::doFactoryBurnInCheck() {
  // Shared by all instances, as the three original function-local statics.
  // Single-threaded caller domain, matching the native unsynchronized cells.
  static std::uint64_t lastTimeMs = 0;
  static bool inBurnInMode = false;
  static std::uint32_t intervalCount = 0;
  const auto now = static_cast<std::uint64_t>(
      presonus::dice::packetClockRawTicks() / 1000000);
  const auto deadline = lastTimeMs + 500u;
  // Native signed high-word and unsigned low-word compare. No signed overflow.
  if ((now ^ (std::uint64_t{1} << 63)) <= (deadline ^ (std::uint64_t{1} << 63)))
    return;
  auto leds = [this] {
    auto *registrar = portableState().registrar;
    if (!registrar)
      throw std::logic_error("RackPanel burn-in registrar is not bound");
    registrar->setAllLeds(true);
  };
  if (inBurnInMode) {
    leds();
    if (portableState().active)
      inBurnInMode = false;
  }
  if (burnInHeldCount != 4)
    intervalCount = 0;
  else {
    ++intervalCount;
    // ARM signed32 increment/compare, including the wrapping bit pattern.
    if (intervalCount > 6 && intervalCount < 0x80000000u) {
      Core::DebugPrintf("FPR: Entering burn-in mode.\n");
      leds();
      inBurnInMode = true;
    }
  }
  // Resample only after all synchronous effects; exceptions leave lastTimeMs.
  lastTimeMs = static_cast<std::uint64_t>(
      presonus::dice::packetClockRawTicks() / 1000000);
}
void RackPanelComponent::onIdle() {
  doFactoryBurnInCheck();
  checkPermissionsPWReset();
  checkNetworkReset();
  idleTasks();
}
} // namespace Presonus::Panel
