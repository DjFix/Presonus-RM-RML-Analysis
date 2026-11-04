#pragma once

#include "presonus/MuteGroupBase.hpp"

// Partial source port. Provider relationships are evidence-backed;
// these declarations do not establish firmware layouts or ARM ABI.
namespace Presonus {
class AllMutesGroup : public MuteGroupBase {
public:
  explicit AllMutesGroup(Mixer::MixerComponentBase &mixer);
  ~AllMutesGroup() override;
  void activate();
};
} // namespace Presonus
