#pragma once

#include "presonus/mixer_dsp/Dsp.hpp"

namespace Presonus::Dsp {
class EQ5Controller : public EQController {
public:
  explicit EQ5Controller(int id);
  ~EQ5Controller() override;
};
} // namespace Presonus::Dsp
