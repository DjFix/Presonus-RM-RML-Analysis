#include "presonus/mixer/RackMixerComponent.hpp"
namespace Presonus::Mixer {
void RackMixerComponent::onCascadeStateChange() {
  base_.onCascadeStateChange();
  if (!base_.isSlave())
    cascadeState_ = 0;
}
} // namespace Presonus::Mixer
