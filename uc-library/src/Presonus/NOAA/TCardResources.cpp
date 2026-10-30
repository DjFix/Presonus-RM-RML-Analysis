#include "core/system/coredebug.h"
#include "presonus/application/ResourceLibrary.hpp"
#include "presonus/noaa/card.hpp"
#include <stdexcept>
namespace {
Presonus::ResourceLibrary &requiredLibrary(presonus::noaa::CardState &state) {
  if (!state.resources)
    throw std::logic_error(
        "TCard status requires a live ResourceLibrary binding");
  return *state.resources;
}
const char *armName(std::uint32_t card) {
  return card == 1 ? "NIMH_ARM" : card == 2 ? "ESA_ARM" : "NOAA_S800ARM";
}
const char *fpgaName(std::uint32_t card) {
  return card == 1 ? "NIMH_FPGA" : card == 2 ? "ESA_FPGA" : "NOAA_S800FPGA";
}
} // namespace
namespace Presonus::NOAA {
Presonus::FirmwareBundle *TCard::getArmFirmwareBundle() {
  return requiredLibrary(state_).get(armName(state_.observedWord14));
}
Presonus::FirmwareBundle *TCard::getFpgaFirmwareBundle() {
  return requiredLibrary(state_).get(fpgaName(state_.observedWord14));
}
bool TCard::isFirmwareCompatible(int mode) {
  auto &resources = requiredLibrary(state_);
  bool arm = false, fpga = false;
  const auto type = state_.observedWord14;
  if (type == 0xffffffffu || type <= 2) {
    const auto requiredArm = resources.getRequiredVersion(armName(type));
    arm = requiredArm == state_.observedWord20;
    const auto requiredFpga = resources.getRequiredVersion(fpgaName(type));
    fpga = requiredFpga == state_.observedWord28;
  }
  if (!arm) {
    const auto expected =
        resources.getRequiredVersion(armName(state_.observedWord14));
    const auto found = state_.observedWord20;
    Core::DebugPrintf(
        "IOCARD: ARM incompatible.  expected:0x%08x found:0x%08x\n", expected,
        found);
  }
  if (!fpga) {
    const auto expected =
        resources.getRequiredVersion(fpgaName(state_.observedWord14));
    const auto found = state_.observedWord28;
    Core::DebugPrintf(
        "IOCARD: FPGA incompatible.  expected:0x%08x found:0x%08x\n", expected,
        found);
  }
  if (mode == 2)
    return arm;
  if (mode == 3)
    return fpga;
  return arm && fpga;
}
} // namespace Presonus::NOAA
