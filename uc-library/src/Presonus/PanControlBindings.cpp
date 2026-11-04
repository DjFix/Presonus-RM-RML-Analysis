#include "presonus/MeterControl.hpp"
#include "presonus/MeterScaleControl.hpp"
#include "presonus/PanControl.hpp"
#include "presonus/surface/MuteGroupsComponent.hpp"
#include "presonus/uc/message_attributes.hpp"
#include "presonus/uc/mutable_message_event.hpp"
#include <stdexcept>

namespace Presonus {
PanControl::PanControl(const Core::Rect &rect, Parameter *parameter)
    : Core::Portable::ValueBar(rect, parameter) {}
void PanControl::setStereoParam(Parameter *parameter) {
  auto *previous = parameters_[0];
  if (previous == parameter)
    return;
  if (previous)
    previous->removeObserver(this);
  parameters_[0] = parameter;
  if (parameter)
    parameter->addObserver(this);
  invalidate();
}
void PanControl::setLinkParam(Parameter *parameter) {
  auto *previous = parameters_[1];
  if (previous == parameter)
    return;
  if (previous)
    previous->removeObserver(this);
  parameters_[1] = parameter;
  if (parameter)
    parameter->addObserver(this);
  invalidate();
}
void PanControl::setChannelNumberParam(Parameter *parameter) {
  auto *previous = parameters_[2];
  if (previous == parameter)
    return;
  if (previous)
    previous->removeObserver(this);
  parameters_[2] = parameter;
  if (parameter)
    parameter->addObserver(this);
  invalidate();
}
void PanControl::setRightSideParam(Parameter *parameter) {
  auto *previous = parameters_[3];
  if (previous == parameter)
    return;
  if (previous)
    previous->removeObserver(this);
  parameters_[3] = parameter;
  if (parameter)
    parameter->addObserver(this);
  invalidate();
}
void PanControl::setStereoPanParam(Parameter *parameter) {
  auto *previous = parameters_[4];
  if (previous == parameter)
    return;
  if (previous)
    previous->removeObserver(this);
  parameters_[4] = parameter;
  if (parameter)
    parameter->addObserver(this);
  invalidate();
}
void PanControl::setAttributes(const Core::Portable::Attributes &attributes) {
  Core::Portable::ValueBar::setAttributes(attributes);
  const char *names[] = {"link", "isstereo", "chnum"};
  for (int i = 0; i < 3; ++i) {
    const char *name = attributes.getString(names[i]);
    if (!name || !*name || !panController_)
      continue;
    auto *p = static_cast<Parameter *>(
        panController_->getObjectForView(name, Core::Portable::kParamType));
    if (i == 0)
      setLinkParam(p);
    else if (i == 1)
      setStereoParam(p);
    else
      setChannelNumberParam(p);
  }
  setImage(Core::Portable::ViewAttributes::getBitmap(attributes, "image"));
  valueBarWidth_ = attributes.getInt("valueBarWidth");
}
} // namespace Presonus
