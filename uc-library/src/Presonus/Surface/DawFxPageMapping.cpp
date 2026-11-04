#include "presonus/surface/DawFxPageComponent.hpp"
namespace Presonus::Surface {
DawFxPageComponent::~DawFxPageComponent() = default;
void DawFxPageComponent::setMappingController(
    Presonus::IMappingController *controller) {
  mappingController_ = controller;
}
} // namespace Presonus::Surface
