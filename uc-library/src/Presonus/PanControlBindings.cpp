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
PanControl::~PanControl() {
  // Native cleanup detaches link before stereo, regardless of lookup order.
  for (std::size_t index : {1, 0, 2, 3, 4})
    removeParameterObserver(index);
}
void PanControl::removeParameterObserver(std::size_t index) {
  if (observesParameter_[index]) {
    parameters_[index]->removeObserver(this);
    observesParameter_[index] = false;
  }
}
void PanControl::setObservedParameter(std::size_t index, Parameter *parameter) {
  const bool changed = parameters_[index] != parameter;
  if (!changed && observesParameter_[index] == (parameter != nullptr))
    return;
  removeParameterObserver(index);
  parameters_[index] = parameter;
  if (parameter) {
    parameter->addObserver(this);
    observesParameter_[index] = true;
  }
  if (changed)
    invalidate();
}
void PanControl::setStereoParam(Parameter *parameter) {
  setObservedParameter(0, parameter);
}
void PanControl::setLinkParam(Parameter *parameter) {
  setObservedParameter(1, parameter);
}
void PanControl::setChannelNumberParam(Parameter *parameter) {
  setObservedParameter(2, parameter);
}
void PanControl::setRightSideParam(Parameter *parameter) {
  setObservedParameter(3, parameter);
}
void PanControl::setStereoPanParam(Parameter *parameter) {
  setObservedParameter(4, parameter);
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
