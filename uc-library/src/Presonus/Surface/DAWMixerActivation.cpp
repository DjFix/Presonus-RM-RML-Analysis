#include "presonus/surface/AssignmentHandlerTable.hpp"
#include "presonus/surface/DAWMixerHandler.hpp"
#include "presonus/surface/MappingComponent.hpp"
#include "presonus/surface/PresetsPageComponent.hpp"
#include <stdexcept>
namespace Presonus::Surface {
bool DAWMixerHandler::canActivate() const {
  return state.clientPresent && ((state.clientActivationFlags ^ 1U) & 1U);
}
const char *DAWMixerHandler::getName() const { return "dawmixer"; }
} // namespace Presonus::Surface
