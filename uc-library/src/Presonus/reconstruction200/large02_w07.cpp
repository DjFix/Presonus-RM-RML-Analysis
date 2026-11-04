#include "presonus/reconstruction200/large02_w07.hpp"
#include <cstring>
#include <stdexcept>
namespace presonus::surface {
namespace {
template <class T> T required(const std::optional<T> &value) {
  if (!value)
    throw std::logic_error("MixerPageView field binding required");
  return *value;
}
} // namespace
MixerPageView &BorrowedMixerPageAccess::view(
    Presonus::MixerClientComponentBase *identity) const {
  if (!identity)
    throw std::logic_error("non-null registered mixer identity required");
  for (int i = 0; i < views_.count(); ++i)
    if (views_.at(i).identity == identity) {
      if (views_.at(i).view->identity != identity)
        throw std::logic_error("registered mixer identity changed");
      return *views_.at(i).view;
    }
  throw std::logic_error("unregistered mixer identity");
}
void BorrowedMixerPageAccess::registerView(MixerPageView &v) {
  if (!v.identity)
    throw std::logic_error("cannot register null mixer identity");
  for (int i = 0; i < views_.count(); ++i) {
    const auto &registered = views_.at(i);
    if (registered.view == &v && registered.identity != v.identity)
      throw std::logic_error("registered view cannot change identity");
    if (registered.identity == v.identity) {
      if (registered.view == &v)
        return;
      throw std::logic_error("duplicate mixer identity");
    }
  }
  views_.add(RegisteredView{v.identity, &v});
}
Core::Portable::Component *
BorrowedMixerPageAccess::groupContainer(Presonus::MixerClientComponentBase *m,
                                        const char *name) {
  auto *tree = required(view(m).groupTree);
  return tree ? tree->findChild(name) : nullptr;
}
Core::Portable::Component *
BorrowedMixerPageAccess::channelContainer(Presonus::MixerClientComponentBase *m,
                                          int kind) {
  if (kind < 0 || kind >= 8)
    throw std::out_of_range("channel container index");
  return required(view(m).channels[kind]);
}
Presonus::MixerClientComponentBase *
BorrowedMixerPageAccess::slaveMixer(Presonus::MixerClientComponentBase *m) {
  return required(view(m).slave);
}
Core::Portable::Component *
BorrowedMixerPageAccess::mixerRoot(Presonus::MixerClientComponentBase *m) {
  return required(view(m).root);
}
Core::Portable::Component *BorrowedMixerPageAccess::selectedChannel(
    Presonus::MixerClientComponentBase *m) {
  return required(view(m).selected);
}

std::int32_t addWrap(std::int32_t a, std::int32_t b) {
  std::uint32_t bits = std::uint32_t(a) + std::uint32_t(b);
  std::int32_t value;
  std::memcpy(&value, &bits, sizeof value);
  return value;
}
} // namespace presonus::surface
namespace Presonus::Surface {
MixerPageComponent::~MixerPageComponent() = default;
SubAssignPageComponent::~SubAssignPageComponent() = default;
presonus::surface::MixerPageAccess &MixerPageComponent::access() const {
  if (!access_)
    throw std::logic_error("MixerPageAccess binding required");
  return *access_;
}
void MixerPageComponent::setMixerComponent(MixerClientComponentBase *p) {
  mixer_ = p;
}
void MixerPageComponent::setMappingController(IMappingController *p) {
  mapping_ = p;
}
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

namespace presonus::surface {
void BorrowedMixerPageAccess::setFilter(Presonus::MixerClientComponentBase *m,
                                        Presonus::ChannelGroupFilter *filter) {
  auto *state = view(m).selectionState;
  if (!state)
    throw std::logic_error("MixerSelectionView binding required");
  state->filter = filter;
}
void BorrowedMixerPageAccess::setSelectedGroup(
    Presonus::MixerClientComponentBase *m, Core::Portable::Component *group) {
  auto *state = view(m).selectionState;
  if (!state)
    throw std::logic_error("MixerSelectionView binding required");
  state->selectedGroup = group;
}
} // namespace presonus::surface
