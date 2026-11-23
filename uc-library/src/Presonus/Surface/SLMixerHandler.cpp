#include "presonus/PageComponent.hpp"
#include "presonus/surface/sl_mixer_encoder.hpp"
namespace Presonus {
void IMixerComponentObserver::onSelectionChanged() {}
void IMixerComponentObserver::onObjectChanged(ObjectChangeMessage) {}
void IMixerComponentObserver::onComponentReplaced(const ReplaceArgs &) {}
} // namespace Presonus

namespace Presonus::Surface {
bool SLMixerHandler::isGeqMode() const {
  return geqPage_ && geqPage_->isVisible();
}
} // namespace Presonus::Surface
