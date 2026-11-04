#include "presonus/reconstruction200/large01_w04.hpp"
#include <stdexcept>
namespace Presonus {
void AssignmentHandlerTable::addHandler(AssignmentHandler *handler) {
  if (handlers_.count() <= 4)
    handlers_.add(handler);
}
namespace Surface {
bool DAWMixerHandler::canActivate() const {
  return state.clientPresent && ((state.clientActivationFlags ^ 1U) & 1U);
}
const char *DAWMixerHandler::getName() const { return "dawmixer"; }
const char *SLMixerHandler::getName() const { return "aimixer"; }
void GeqPageComponent::addObserver(IObserver *observer) {
  if (observers_.count() <= 9)
    observers_.add(observer);
}
int GeqPageComponent::getMaxListOffset() { return 15; }
int SLMixerHandler::getGeqScrollOffset() const {
  if (!presonus::surface::SLMixerEncoderAccess::hasGeqPage(*this))
    return 0;
  auto *view = presonus::surface::SLMixerEncoderAccess::scrollView(*this);
  if (!view)
    throw std::logic_error(
        "GEQ page requires an explicit portable scroll binding");
  return presonus::surface::PageObserverAccess::listOffset(*view);
}

void EQPageComponent::addObserver(IObserver *observer) {
  if (observers_.count() <= 9)
    observers_.add(observer);
}
void PresetsPageComponent::setMappingController(
    IMappingController *controller) {
  state.mappingController = controller;
}
bool MappingComponent::areFadersLockedToMainMix() const {
  return fadersLockedToMainMix_;
}
} // namespace Surface
} // namespace Presonus
