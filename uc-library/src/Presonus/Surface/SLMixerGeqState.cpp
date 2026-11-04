#include "presonus/surface/AssignmentHandlerTable.hpp"
#include "presonus/surface/DAWMixerHandler.hpp"
#include "presonus/surface/MappingComponent.hpp"
#include "presonus/surface/PresetsPageComponent.hpp"
#include <stdexcept>
namespace Presonus::Surface {
const char *SLMixerHandler::getName() const { return "aimixer"; }
int SLMixerHandler::getGeqScrollOffset() const {
  if (!presonus::surface::SLMixerEncoderAccess::hasGeqPage(*this))
    return 0;
  auto *view = presonus::surface::SLMixerEncoderAccess::scrollView(*this);
  if (!view)
    throw std::logic_error(
        "GEQ page requires an explicit portable scroll binding");
  return presonus::surface::PageObserverAccess::listOffset(*view);
}

} // namespace Presonus::Surface
