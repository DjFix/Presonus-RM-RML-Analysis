#include "presonus/mixer_update/FirmwareUpdateComponent.hpp"
#include "presonus/surface_update/CallbackText.hpp"
#include <stdexcept>
namespace Presonus::Mixer {
FirmwareUpdateComponent::FirmwareUpdateComponent(
    presonus::mixer_update::CallbackSourcePort,
    const Core::Portable::ParamInfo *parameters, int count,
    Core::Portable::Parameter *progress, UC::IFirmwareUpdateListener *listener)
    : Core::Portable::Component("firmwareUpdate"), progressParameter(progress),
      progressListener(listener) {
  if (count > 0)
    addParameters(parameters, count);
}
void FirmwareUpdateComponent::setText(const char *title, const char *message) {
  presonus::surface_update::setCallbackText(*this, title, message);
}
void FirmwareUpdateComponent::onProgress(const char *title, const char *message,
                                         float progress) {
  setText(title, message);
  if (progressParameter)
    progressParameter->setValue(progress, false);
  if (progressListener)
    progressListener->onProgress(title, progress);
}
void FirmwareUpdateComponent::dismissAlert() {
  auto *p = countParameters() > 0 ? getParameterByTag(4) : nullptr;
  if (!p)
    throw std::logic_error("RM updater requires parameter tag4");
  p->setValue(0.f, true);
  setText("", "");
}
void FirmwareUpdateComponent::doAlert(const char *alert, const char *title,
                                      const char *message) {
  presonus::surface_update::setCallbackAlert(*this, alert, title, message);
}
} // namespace Presonus::Mixer
