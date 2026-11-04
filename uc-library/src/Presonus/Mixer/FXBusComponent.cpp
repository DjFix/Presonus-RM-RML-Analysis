#include "presonus/mixer/FXBusComponent.hpp"
namespace Presonus::Mixer {
void FXBusComponent::paramChanged(Core::Portable::Parameter *parameter,
                                  int message) {
  send_.paramChanged(parameter, message);
  const int tag = parameter->getTag();
  if (message != 3 || tag != 410)
    return;
  state_.output.updatePending = true;
  for (auto *child : children_) {
    child->fxChanged = 1;
    child->output.updatePending = true;
  }
}
} // namespace Presonus::Mixer
