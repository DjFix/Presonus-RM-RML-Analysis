#include "presonus/mixer_dsp/EQ4Controller.hpp"
#include "presonus/mixer_dsp/EqParameterLists.hpp"
#include <bit>

namespace Presonus::Dsp {

static_assert(sizeof(EQ4CoefficientsProperty) == 0x50);

EQ4Controller::EQ4Controller(int id)
    : EQController(4, id,
                   &presonus::dsp::sourceList(*EqParamList::instance())) {
  sourceState().word08 = 0;
  setDefaultValues();
}

EQ4Controller::~EQ4Controller() = default;

void EQ4Controller::doUpdates() {
  EQ4CoefficientsProperty property;
  double gain = 1.;
  for (unsigned index = 0; index < 4; ++index) {
    auto &band = portableBands()[index];
    if (band.dirty) {
      band.calculator.setParams(band.type, band.frequency, band.q, band.gain);
      band.dirty = 0;
    }

    if (portableEnabled() && band.enabled) {
      const auto &coefficients = band.calculator.portableState().coefficients;
      const double leading = coefficients[0];
      gain *= leading;
      property.firstNumerator[index] =
          static_cast<float>(coefficients[2] / leading);
      property.secondNumerator[index] =
          static_cast<float>(coefficients[4] / leading);
      property.firstFeedback[index] = static_cast<float>(-coefficients[1]);
      property.secondFeedback[index] = static_cast<float>(-coefficients[3]);
    } else {
      band.calculator.flush();
      property.firstFeedback[index] = -0.f;
      property.secondFeedback[index] = -0.f;
    }

    if (band.dirty)
      sourceState().processDirty = 1;
  }
  property.gain = static_cast<float>(gain);
  // The original channel overload stamps this field before synchronous
  // delivery. The portable overload has a different payload shape.
  property.channel = std::bit_cast<int>(sourceState().word04);
  sendProperty(property);
}

} // namespace Presonus::Dsp
