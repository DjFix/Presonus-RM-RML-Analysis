#include "presonus/DAWClientComponent.hpp"

#include "core/public/coreformatter.h"

namespace Presonus {
namespace {
constexpr std::uint32_t progressFlag = 1U << 1;
constexpr auto progressChange =
    static_cast<IDAWComponentObserver::ObjectChangeMessage>(2);
} // namespace

IDAWTimeInfoFactory *DAWClientComponent::timeInfoFactory_ = nullptr;

void *DAWClientComponent::castTo(int typeId) {
  if (typeId == kTypeID)
    return this;
  return ClientRootComponent::castTo(typeId);
}

DAWChannel *DAWClientComponent::getFocusChannel() { return focusChannel_; }

void DAWClientComponent::setFocusChannel(DAWChannel *channel) {
  if (focusChannel_ == channel)
    return;

  focusChannel_ = channel;
  for (int index = 0, count = observers_.count(); index < count; ++index)
    observers_.at(index)->onFocusChannelChanged();
}

void DAWClientComponent::channelsChanged(DAWChannelGroup *group) {
  for (int index = 0, count = observers_.count(); index < count; ++index)
    observers_.at(index)->onChannelsChanged(group);
}

void DAWClientComponent::slotCountChanged(DAWDeviceFolder *folder) {
  for (int index = 0, count = observers_.count(); index < count; ++index)
    observers_.at(index)->onSlotCountChanged(folder);
}

void DAWClientComponent::slotEditChanged(DAWDeviceSlot *slot, bool edit) {
  for (int index = 0, count = observers_.count(); index < count; ++index)
    observers_.at(index)->onSlotEditChanged(slot, edit);
}

void DAWClientComponent::sendObjectChangeMessage(
    IDAWComponentObserver::ObjectChangeMessage message) {
  for (int index = 0, count = observers_.count(); index < count; ++index)
    observers_.at(index)->onObjectChanged(message);
}

bool DAWClientComponent::isDAWProgressMode() const {
  return (dawFlags_ & progressFlag) != 0;
}

void DAWClientComponent::setDAWProgress(bool active) {
  if (isDAWProgressMode() == active)
    return;

  dawFlags_ = active ? dawFlags_ | progressFlag : dawFlags_ & ~progressFlag;
  sendObjectChangeMessage(progressChange);
}

Core::Portable::Parameter *DAWClientComponent::getLoopStartParam() const {
  return paramList.byTag(0);
}

Core::Portable::Parameter *DAWClientComponent::getLoopEndParam() const {
  return paramList.byTag(1);
}

void DAWClientComponent::setDialogHandler(IDAWDialogHandler *handler) {
  dialogHandler_ = handler;
}

IDAWTimeInfo *DAWClientComponent::getTimeInfo() const { return timeInfo_; }

void DAWClientComponent::setTimeInfoFactory(IDAWTimeInfoFactory *factory) {
  timeInfoFactory_ = factory;
}

void DAWClientComponent::optimize() {
  Core::CStringPtr names[]{"gain.db.value", "pan.100", "gain.0", "bpm.value",
                           nullptr};
  Core::FormatterRegistry::optimize(names);
}

Core::Portable::Component *DAWClientComponent::getMixer() const {
  return findChild("mixer");
}

Core::Portable::Component *DAWClientComponent::getControlLink() const {
  return findChild("controls");
}

Core::Portable::Component *DAWClientComponent::getDocument() const {
  return findChild("document");
}

Core::Portable::Component *DAWClientComponent::getRecordDiskSpace() const {
  return findChild("recorddiskspace");
}

Core::Portable::Component *DAWClientComponent::getSessionComponent() const {
  return findChild("session");
}

Core::Portable::Component *DAWClientComponent::getRecordPanelComponent() const {
  return findChild("recordpanel");
}

Core::Portable::Component *DAWClientComponent::getMetronomeComponent() const {
  return findChild("metronome");
}

bool DAWClientComponent::addSourcePortObserver(
    IDAWComponentObserver &observer) {
  return observers_.add(&observer);
}

bool DAWClientComponent::removeSourcePortObserver(
    IDAWComponentObserver &observer) {
  return observers_.remove(&observer);
}

} // namespace Presonus
