#include "presonus/mixer_dsp/EQControl.hpp"
// Original global internal-linkage identity retained. The int array and const
// declaration are portable choices; original C++ datatype is unestablished.
static const int eqBiquadTypes[4] = {3, 8, 9, 6};
int Presonus::EQControl::getBiquadType(int index) const {
  return index > 3 ? 6 : eqBiquadTypes[index];
}
