#include "presonus/surface/MixerPageComponent.hpp"
#include "presonus/surface/SubAssignPageComponent.hpp"
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
