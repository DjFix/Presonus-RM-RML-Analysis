#include "presonus/rank20cycle01/rank20c01_w04.hpp"
#include "presonus/PageComponent.hpp"
#include "presonus/surface/DAWMixerHandler.hpp"
#include "presonus/surface/sl_mixer_encoder.hpp"
#include <cstdint>
namespace Presonus::Surface {
bool DAWLoadDocumentPage::onOk() {
  void *document = bindings_.selectedDocument();
  if (!document)
    return false;
  bindings_.loadDocument(document);
  return true;
}
bool DAWMixerHandler::shouldShowStripEncodersAsMeters() const {
  const int mode = state.mappingController
                       ? state.mappingController->getRadioValue(34, 37)
                       : -1;
  return (static_cast<std::uint32_t>(mode) >> 31) != 0;
}
bool SLMixerHandler::isGeqMode() const {
  return geqPage_ && geqPage_->isVisible();
}
} // namespace Presonus::Surface
