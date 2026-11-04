#include "presonus/frontier01/frontier01_w02.hpp"
#include <stdexcept>
namespace Presonus::Mixer {
Core::Portable::FileName GlobalComponent::getTempFilePath() {
  if (!mixer_)
    throw std::logic_error("GlobalComponent requires a live mixer binding");
  auto path = mixer_->getDataDir("temp");
  path.descend("mixer.scene");
  return path;
}
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
