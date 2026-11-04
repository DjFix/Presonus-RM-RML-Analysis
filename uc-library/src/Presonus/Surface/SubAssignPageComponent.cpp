#include "presonus/surface/SubAssignPageComponent.hpp"
#include "presonus/surface/MixerPageComponent.hpp"
#include <cstring>
#include <stdexcept>
namespace Presonus::Surface {
SubAssignPageComponent::~SubAssignPageComponent() = default;
void SubAssignPageComponent::buildItemsList() {
  if (!mixer_)
    return;
  items.resize(0);
  auto append = [this](Core::Portable::Component *container) {
    if (container)
      for (int i = 0; i < container->countChildren(); ++i)
        items.add(container->getChild(i));
  };
  append(access().channelContainer(mixer_, 0));
  if (auto *slave = access().slaveMixer(mixer_))
    append(access().channelContainer(slave, 0));
  append(access().channelContainer(mixer_, 2));
}
int SubAssignPageComponent::getMaxListOffset() const {
  int result = presonus::surface::addWrap(items.count(), -16);
  return result < 0 ? 0 : result;
}
void SubAssignPageComponent::setListOffset(int offset) {
  int bounded = offset < 0                    ? 0
                : offset < getMaxListOffset() ? offset
                                              : getMaxListOffset();
  if (listOffset == bounded)
    return;
  listOffset = bounded;
  updateParams();
}
void SubAssignPageComponent::addListOffset(int delta) {
  setListOffset(presonus::surface::addWrap(listOffset, delta));
}
void SubAssignPageComponent::paramChanged(Core::Portable::Parameter *p,
                                          int msg) {
  if (msg != 2)
    return;
  if (p->getTag() == 100) {
    if (p->getValue() > 0)
      addListOffset(-4);
  } else if (p->getTag() == 101) {
    if (p->getValue() > 0)
      addListOffset(4);
  }
}
} // namespace Presonus::Surface

namespace Presonus::Surface {
void SubAssignPageComponent::updateParams() {
  if (!page_)
    throw std::logic_error("real PageComponent visibility binding required");
  if (!page_->isVisible())
    return;
  buildItemsList();
  if (!mixer_)
    return;
  auto *subs = access().channelContainer(mixer_, 4);
  if (!subs)
    return;
  auto *selected = access().selectedChannel(mixer_);
  int index = 0;
  for (; index < subs->countChildren(); ++index)
    if (subs->getChild(index) == selected)
      break;
  if (index == subs->countChildren() || index > 15)
    return;
  for (int row = 0; row < 16; ++row) {
    Core::CString32 assign("assign_slot"), name("assign_slot_name");
    assign.appendFormat("_%02d", row + 1);
    name.appendFormat("_%02d", row + 1);
    auto *assignment = Core::Portable::AliasParam::cast(findParameter(assign));
    auto *label = Core::Portable::AliasParam::cast(findParameter(name));
    int at = presonus::surface::addWrap(listOffset, row);
    auto *item = at >= 0 && at < items.count() ? items.at(at) : nullptr;
    if (label)
      label->setOriginal(item ? item->getParameterByTag(1) : nullptr);
    if (assignment)
      assignment->setOriginal(item ? item->getParameterByTag(index + 256)
                                   : nullptr);
  }
}
} // namespace Presonus::Surface
