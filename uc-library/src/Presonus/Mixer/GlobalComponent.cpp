#include "presonus/mixer/GlobalComponent.hpp"
namespace Presonus::Mixer {
GlobalComponent::~GlobalComponent() = default;
} // namespace Presonus::Mixer

#include "presonus/mixer/GlobalComponent.hpp"
#include <stdexcept>
namespace Presonus::Mixer {
Core::Portable::FileName GlobalComponent::getTempFilePath() {
  if (!mixer_)
    throw std::logic_error("GlobalComponent requires a live mixer binding");
  auto path = mixer_->getDataDir("temp");
  path.descend("mixer.scene");
  return path;
}
} // namespace Presonus::Mixer
