#include "presonus/surface_update/CallbackText.hpp"
#include "presonus/surface_update/FirmwareUpdateComponent.hpp"
namespace Presonus::Surface {
FirmwareUpdateComponent::FirmwareUpdateComponent(
    presonus::surface_update::CallbackSourcePort,
    const Core::Portable::ParamInfo *parameters, int parameterCount,
    Core::Portable::Parameter *progress)
    : Core::Portable::Component("firmwareUpdate"), progressParameter(progress) {
  if (parameterCount > 0)
    addParameters(parameters, parameterCount);
}
void FirmwareUpdateComponent::setText(const char *title, const char *message) {
  presonus::surface_update::setCallbackText(*this, title, message);
}
void FirmwareUpdateComponent::onProgress(const char *title, const char *message,
                                         float progress) {
  setText(title, message);
  if (progressParameter)
    progressParameter->setValue(progress, false);
}
void FirmwareUpdateComponent::dismissAlert() {
  if (progressParameter)
    progressParameter->setValue(0.f, true);
  setText("", "");
}
void FirmwareUpdateComponent::doAlert(const char *alert, const char *title,
                                      const char *message) {
  presonus::surface_update::setCallbackAlert(*this, alert, title, message);
}
} // namespace Presonus::Surface
