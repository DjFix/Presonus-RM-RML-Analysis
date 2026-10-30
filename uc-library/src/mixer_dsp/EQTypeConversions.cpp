#include "presonus/mixer_dsp/Dsp.hpp"
#include <cstddef>

namespace {
// Independent constant mirrors of separately hash-verified original data.
// Original array element declarations remain unresolved.
constexpr int eqCodes[] = {3, 8, 9, 6};
constexpr int eq8Codes[] = {6, 12, 10, 8, 9, 7, 3, 2};
template <std::size_t N>
int findType(DSP::BiquadType value, const int (&codes)[N]) {
  for (std::size_t index = 0; index < N; ++index)
    if (static_cast<int>(value) == codes[index])
      return static_cast<int>(index);
  return 3;
}
} // namespace

namespace Presonus::Dsp {
int EQController::getEQType(DSP::BiquadType type) const {
  return findType(type, eqCodes);
}
int EQ8Controller::getEQType(DSP::BiquadType type) const {
  return findType(type, eq8Codes);
}
int EQController::getBiquadType(int index) const {
  if (index > 3)
    return 6;
  return eqCodes[index];
}
int EQ8Controller::getBiquadType(int index) const {
  if (index > 7)
    return 6;
  return eq8Codes[index];
}
} // namespace Presonus::Dsp
