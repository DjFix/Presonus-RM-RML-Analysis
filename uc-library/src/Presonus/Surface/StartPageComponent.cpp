#include "presonus/surface/StartPageComponent.hpp"
namespace Presonus::Surface {
StartPageComponent::~StartPageComponent() = default;
bool StartPageComponent::isDawMode() const {
  return getParameterByTag(1000)->getValue() == 1.0f;
}
bool StartPageComponent::isMidiMode() const {
  return getParameterByTag(1001)->getValue() == 1.0f;
}
} // namespace Presonus::Surface
