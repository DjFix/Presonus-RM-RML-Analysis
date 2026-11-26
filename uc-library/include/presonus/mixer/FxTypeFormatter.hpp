#pragma once

#include "presonus/mixer/NumberPrepender.hpp"

namespace Presonus::Mixer {

class FxTypeFormatter : public NumberPrepender {
public:
  FxTypeFormatter();
  ~FxTypeFormatter() override;
};

} // namespace Presonus::Mixer
