#include "presonus/mixer_dsp/Dsp.hpp"
#include "presonus/mixer_dsp/EqParameterLists.hpp"

namespace Presonus::Dsp {
EQ8Controller::EQ8Controller(int id)
    : EQController(8, id,
                   &presonus::dsp::sourceList(*Eq8ExtParamList::instance())) {
  setDefaultValues();
}

EQ8Controller::~EQ8Controller() = default;
} // namespace Presonus::Dsp
