#pragma once
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/mixer/OutputComponent.hpp"
#include <cstdint>
#include <vector>

namespace Presonus::Mixer {
// Partial source-port facades. Composition is intentional: no original complete
// inheritance, field layout, ownership or unencoded return declaration claim.
class RackMixerComponent {
public:
  RackMixerComponent(MixerComponentBase &base, std::uint32_t &cascadeState)
      : base_(base), cascadeState_(cascadeState) {}
  void onCascadeStateChange();

private:
  MixerComponentBase &base_;
  std::uint32_t &cascadeState_;
};
} // namespace Presonus::Mixer
