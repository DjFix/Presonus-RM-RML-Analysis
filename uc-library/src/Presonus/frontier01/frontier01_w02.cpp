#include "presonus/frontier01/frontier01_w02.hpp"
namespace Presonus::Mixer {
void RackMixerComponent::onCascadeStateChange() {
  base_.onCascadeStateChange();
  if (!base_.isSlave())
    cascadeState_ = 0;
}
void SendOutputComponent::paramChanged(Core::Portable::Parameter *parameter,
                                       int message) {
  const int tag = parameter->getTag(); // original reads before Output callback
  base_.paramChanged(parameter, message);
  if (message == 2) {
    if (tag == 21)
      for (auto *child : children_) {
        child->childChanged = 1;
        child->output.updatePending = true;
      }
    return;
  }
  if (message != 3)
    return;
  if (tag == 14) {
    for (auto *child : children_) {
      child->output.outputCoeffChanged = 1;
      child->output.updatePending = true;
    }
    state_.output.outputCoeffChanged = 1;
    state_.output.updatePending = true;
  } else if (tag == 412 || tag == 413) {
    state_.sendChanged = 1;
    state_.output.updatePending = true;
  }
}
GlobalComponent::~GlobalComponent() = default;
GEQLinkHandler::~GEQLinkHandler() = default;
} // namespace Presonus::Mixer
