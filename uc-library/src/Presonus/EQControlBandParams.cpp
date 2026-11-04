#include "presonus/mixer_dsp/Dsp.hpp"
#include "presonus/mixer_dsp/EQControl.hpp"
#include <bit>
#include <cstring>
#include <stdexcept>
namespace Presonus {
bool EQControl::BandParams::contains(Core::Portable::Parameter *p) const {
  return gain == p || q == p || frequency == p || slot3 == p || slot4 == p ||
         slot5 == p;
}
void EQControl::BandParams::zeroParam(Core::Portable::Parameter *p) {
  // Native is a first-match operation and deliberately does not clear slot5.
  if (gain == p)
    gain = nullptr;
  else if (q == p)
    q = nullptr;
  else if (frequency == p)
    frequency = nullptr;
  else if (slot3 == p)
    slot3 = nullptr;
  else if (slot4 == p)
    slot4 = nullptr;
}
bool EQControl::isBufferedDraw() const { return bufferedDraw; }
} // namespace Presonus
