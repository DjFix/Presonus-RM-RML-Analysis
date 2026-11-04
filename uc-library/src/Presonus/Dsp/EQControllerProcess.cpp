#include "presonus/mixer_dsp/Dsp.hpp"
#include "presonus/mixer_dsp/EQControl.hpp"
#include <bit>
#include <cstring>
#include <stdexcept>
namespace Presonus::Dsp {
int EQController::getNumBands() const {
  return static_cast<int>(bands_.size());
}
void EQController::triggerOption(int index) {
  if (index < 0 || index >= getNumBands())
    return;
  auto &band = bands_[static_cast<unsigned>(index)];
  const int old = band.type;
  // Independently executed native table selections yield 8,9,6 for
  // first-edge, last-edge and all remaining bands respectively.
  band.type = band.edgeSelectable ? (index == 0                   ? 8
                                     : index == getNumBands() - 1 ? 9
                                                                  : 6)
                                  : 6;
  if (!controllerState_.processDirty)
    controllerState_.processDirty = band.type != old;
}
void EQController::setupProcess(const SetupProperty &property) {
  std::uint32_t bits;
  std::memcpy(&bits, reinterpret_cast<const std::byte *>(&property) + 8, 4);
  const float rate = std::bit_cast<float>(bits);
  if (rate == std::bit_cast<float>(controllerState_.processRateBits))
    return;
  controllerState_.processRateBits = bits;
  for (auto &band : bands_) {
    band.calculator.setup(32, static_cast<double>(rate));
    band.dirty = 1;
  }
  controllerState_.processDirty = 1;
}
} // namespace Presonus::Dsp
