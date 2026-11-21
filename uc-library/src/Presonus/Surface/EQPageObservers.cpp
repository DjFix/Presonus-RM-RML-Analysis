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
void EQPageComponent::paramChanged(Core::Portable::Parameter *parameter,
                                   int message) {
  if (parameter->getTag() != 1000 || message != 2)
    return;
  const int count = observers_.count();
  auto *const *observers = observers_.getItems();
  for (int index = 0; index < count; ++index)
    observers[index]->onEqEncoderModeChanged();
}
} // namespace Presonus::Surface
