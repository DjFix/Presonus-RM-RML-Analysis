#include "presonus/surface/PageHeaderComponent.hpp"
#include "presonus/surface/AssignmentHandlerTable.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"

namespace Presonus::Surface {
void PageHeaderComponent::disconnectMappables() {
  MappablePageComponent::disconnectMappables();
  if (label_)
    label_->fromString("", false);
}

void PageHeaderComponent::updateFocusParam(
    Core::Portable::Parameter *parameter) {
  if (!focus_ || !label_)
    return;
  if (!parameter) {
    focus_->setOriginal(nullptr);
    label_->fromString("", false);
    return;
  }

  auto *original = parameter->getOriginal();
  if (!original || original == focus_->getOriginal())
    return;

  MixerAssignmentHandler::FocusInfo info;
  if (!assignments_->getParamFocusInfo(info, original))
    return;

  auto *alternate = info.sourcePort.alternateOriginal;
  focus_->setOriginal(alternate ? alternate : original);
  label_->fromString(info.sourcePort.label, false);
}
} // namespace Presonus::Surface
