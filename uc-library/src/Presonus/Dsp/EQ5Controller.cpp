#include "presonus/mixer_dsp/EQ5Controller.hpp"

#include "presonus/mixer_dsp/Eq8LimiterParameterLists.hpp"

namespace Presonus::Dsp {
EQ5Controller::EQ5Controller(int id)
    : EQController(8, id,
                   &presonus::dsp::sourceList(*Eq8ParamList::instance())) {
  setDefaultValues();
}

EQ5Controller::~EQ5Controller() = default;
} // namespace Presonus::Dsp
