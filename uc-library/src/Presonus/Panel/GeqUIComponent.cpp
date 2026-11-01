#include "presonus/panel/GeqUIComponent.hpp"
#include <cstdint>
namespace Presonus::Panel {
Mixer::GEQComponent *GeqUIComponent::geqAt(int index) const {
  return index >= 0 && index < dependencies.geqCount()
             ? dependencies.geqAt(index)
             : nullptr;
}
bool GeqUIComponent::isChildParameter(
    const Core::Portable::Parameter &p) const {
  for (int i = 0; i < countParameters(); ++i)
    if (getParameterAt(i) == &p)
      return true;
  return false;
}
bool GeqUIComponent::isChannelLinked(unsigned int index) {
  auto *geq = geqAt(static_cast<std::int32_t>(index));
  if (!geq)
    return false;
  auto *p = dependencies.parameters(geq).getParameterByTag(32);
  return p && p->getValue() > 0.f;
}
Mixer::GEQComponent *
GeqUIComponent::getGeqForChannel(Mixer::ChannelComponent *channel) {
  if (!channel)
    return nullptr;
  const auto index = dependencies.channelKind(channel) == 4
                         ? dependencies.channelIndex(channel) + 2u
                         : 0u;
  return geqAt(static_cast<std::int32_t>(index));
}
void GeqUIComponent::flattenCurrentGeq() {
  auto *geq = geqAt(currentGeq);
  if (!geq)
    return;
  if (dependencies.linked(geq) && dependencies.linkSlave(geq))
    geq = geqAt(currentGeq ^ 1);
  if (geq)
    dependencies.flatten(geq);
}
void GeqUIComponent::addRemoveWatchers(int index, bool add) {
  if (index < 0)
    return;
  auto *geq = geqAt(index);
  if (!geq)
    return;
  for (int tag = 0; tag < 32; ++tag)
    if (auto *p = dependencies.parameters(geq).getParameterByTag(tag)) {
      if (add)
        p->addObserver(this);
      else
        p->removeObserver(this);
    }
}
void GeqUIComponent::selectBand(int band) {
  auto *geq = geqAt(currentGeq);
  if (!geq)
    return;
  auto *alias = Core::Portable::core_cast<Core::Portable::AliasParam>(
      getParameterByTag(2));
  auto *original = dependencies.parameters(geq).getParameterByTag(band);
  if (alias)
    alias->setOriginal(original);
}
void GeqUIComponent::updateBandSelect() {
  auto *p = getParameterByTag(1);
  float selected = static_cast<float>(currentBand);
  if (p->getValue() != selected)
    p->setValue(selected, true);
}
void GeqUIComponent::updateStereoField() {
  auto *channel = dependencies.assignedChannel(currentGeq);
  bool stereo = channel && (dependencies.linked(channel) ||
                            dependencies.channelKind(channel) == 7);
  if (auto *p = getParameterByTag(5))
    p->setValue(stereo ? 1.f : 0.f, false);
  if (auto *geq = geqAt(currentGeq))
    if (auto *p = dependencies.parameters(geq).getParameterByTag(32))
      p->enable(stereo);
}
void GeqUIComponent::updateStereoLink(Mixer::ChannelComponent *channel,
                                      bool update) {
  if (!channel)
    channel = dependencies.assignedChannel(currentGeq);
  bool stereo = false;
  bool linked = false;
  if (channel) {
    stereo = dependencies.channelKind(channel) == 7;
    stereo = dependencies.channelLink(channel).getValue() > 0.f || stereo;
    linked =
        dependencies.parameters(channel).getParameterByTag(22)->getValue() >
        0.f;
  }
  if (auto *geq = getGeqForChannel(channel))
    if (auto *p = dependencies.parameters(geq).getParameterByTag(32)) {
      if (!stereo)
        p->setValue(0.f, true);
      if (update && stereo && linked)
        p->setValue(1.f, true);
    }
  updateStereoField();
}
void GeqUIComponent::observedParamChanged(Core::Portable::Parameter *p,
                                          int message) {
  if (!p)
    return;
  if (message == 5) {
    p->removeObserver(this);
    return;
  }
  if (message != 3)
    return;
  if (auto *geq = dependencies.geqController(p->getController())) {
    (void)geq;
    int tag = p->getTag();
    if (tag >= 0) {
      if (tag <= 30)
        currentBand = tag;
      if (tag == 32)
        dependencies.updateGeqNameList();
    }
  }
  if (auto *channel = dependencies.channelController(p->getController())) {
    updateStereoLink(channel, dependencies.channelUpdateLink(channel));
    dependencies.updateGeqNameList();
  }
}
} // namespace Presonus::Panel
