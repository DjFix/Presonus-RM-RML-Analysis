#include "presonus/surface/AssignmentHandlerTable.hpp"
#include "presonus/surface/DAWMixerHandler.hpp"
#include "presonus/surface/MappingComponent.hpp"
#include "presonus/surface/PresetsPageComponent.hpp"
#include <stdexcept>
namespace Presonus::Surface {
void EQPageComponent::addObserver(IObserver *observer) {
  if (observers_.count() <= 9)
    observers_.add(observer);
}
} // namespace Presonus::Surface
