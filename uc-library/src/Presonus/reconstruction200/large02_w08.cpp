#include "presonus/reconstruction200/large02_w08.hpp"
#include "presonus/MeterControl.hpp"
#include "presonus/PanControl.hpp"
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
} // namespace Presonus

namespace Presonus {
MeterControl::MeterControl(const Core::Rect &rect)
    : Core::Portable::Control(rect, nullptr) {}
void MeterControl::connect(void *object) {
  Core::Portable::Control::connect(object);
  if (auto *p = getParameter())
    setValue(p->getNormalized());
}
MeterScaleControl::MeterScaleControl(const Core::Rect &rect)
    : Core::Portable::Control(rect, nullptr) {}
MeterScaleControl::~MeterScaleControl() = default;
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
namespace Surface {
void MuteGroupsComponent::paramChanged(Parameter *p, int msg) {
  Core::Portable::Component::paramChanged(p, msg);
  const int tag = p->getTag();
  const bool group = static_cast<unsigned>(tag) <= 7u;
  const int index = group ? tag : tag - 8;
  if (msg == 0) {
    if (group) {
      if (auto *t = timer(index))
        t->beginAction(-1.f);
    }
    return;
  }
  if (msg == 2) {
    if (group)
      p->setValue(p->getValue() > 0.f ? 0.f : 1.f, false);
    return;
  }
  if (msg == 3) {
    if (!group)
      if (auto *target = getParameterByTag(index))
        target->setValue(p->getValue(), false);
    return;
  }
  if (msg != 1 || !group)
    return;
  auto *t = timer(index);
  if (!t)
    return;
  if (t->isExecuting()) {
    p->setValue(p->getValue() > 0.f ? 0.f : 1.f, false);
    if (auto *target = getParameterByTag(index + 8))
      target->setValue(p->getValue(), true);
  }
  t->reset();
}
void MuteGroupsComponent::storeMuteGroup(int index) {
  auto *p = getParameterByTag(index);
  if (p && p->getValue() != 0.f) {
    p->setValue(0.f, false);
    refresh_.beginAction(-1.f);
  }
  UC::MessageAttributes attributes("presetMuteGroup");
  attributes.setURL("mutegroup");
  attributes.set("presetMuteGroupIndex", static_cast<Core::int64>(index));
  UC::MutableMessageEvent event(attributes, 0x4a4d, 0);
  if (client_) {
    if (!origins_)
      throw std::logic_error(
          "MuteGroupsComponent requires message origin binding");
    const auto &message =
        presonus::uc::MutableMessageEventPortAccess::event(event);
    auto binding = origins_->bind(message);
    client_->sendEvent(const_cast<UC::Event &>(message.header));
  }
}
void MuteGroupsComponent::onIdle() {
  Core::Portable::Component::onIdle();
  const auto count = timers_.size();
  for (std::size_t i = 0; i < count; ++i) {
    auto *t = timer(static_cast<int>(i));
    if (t && t->isExecuting() && t->isLongEnoughYet()) {
      t->endAction();
      storeMuteGroup(static_cast<int>(i));
    }
  }
  if (refresh_.isExecuting() && refresh_.isLongEnoughYet()) {
    refresh_.reset();
    for (int tag = 8; tag < 16; ++tag)
      if (auto *p = getParameterByTag(tag))
        p->changed();
  }
}
} // namespace Surface
} // namespace Presonus
