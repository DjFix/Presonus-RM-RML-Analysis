#include "presonus/mixer_dsp/Dsp.hpp"
#include "presonus/mixer_dsp/EQControl.hpp"
#include <bit>
#include <cstring>
#include <stdexcept>
namespace Presonus::Dsp {
float ShelbyGEQController::getValue(int index) const {
  if (index > 32)
    return 0.f;
  if (index < 0)
    throw std::out_of_range("Unchecked original negative index");
  return values_[static_cast<unsigned>(index)];
}
int ShelbyGEQController::getNumParameters() const { return 33; }
} // namespace Presonus::Dsp
