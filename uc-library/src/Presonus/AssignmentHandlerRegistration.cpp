#include "presonus/surface/AssignmentHandlerTable.hpp"
#include "presonus/surface/DAWMixerHandler.hpp"
#include "presonus/surface/MappingComponent.hpp"
#include "presonus/surface/PresetsPageComponent.hpp"
#include <stdexcept>
namespace Presonus {
void AssignmentHandlerTable::addHandler(AssignmentHandler *handler) {
  if (handlers_.count() <= 4)
    handlers_.add(handler);
}
} // namespace Presonus
