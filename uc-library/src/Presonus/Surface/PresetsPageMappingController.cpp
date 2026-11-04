#include "presonus/surface/AssignmentHandlerTable.hpp"
#include "presonus/surface/DAWMixerHandler.hpp"
#include "presonus/surface/MappingComponent.hpp"
#include "presonus/surface/PresetsPageComponent.hpp"
#include <stdexcept>
namespace Presonus::Surface {
void PresetsPageComponent::setMappingController(
    IMappingController *controller) {
  state.mappingController = controller;
}
} // namespace Presonus::Surface
