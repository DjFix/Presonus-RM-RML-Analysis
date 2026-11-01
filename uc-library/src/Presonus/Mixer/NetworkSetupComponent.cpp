#include "presonus/mixer/NetworkSetupComponent.hpp"
#include "core/system/coretime.h"
#include <cstring>

namespace Presonus::Mixer {
void NetworkSetupComponent::onIdle() {
  if (state_.hasRemoteHandler)
    state_.services.remoteIdle();
  checkRestoreMixer();
}
UC::ClientRootComponent *NetworkSetupComponent::getConnectedClient() const {
  return state_.selected ? state_.services.component(*state_.selected)
                         : nullptr;
}
int NetworkSetupComponent::sendEvent(UC::Event &event) {
  if (!getConnectedClient())
    return 0;
  // Preserve both original lookups. An initialized, stable application boundary
  // is required, as in the native path; the second result is not cached.
  return state_.services.eventSender(*getConnectedClient()).sendEvent(event);
}
void NetworkSetupComponent::onNetworkItemAdded(UC::NetworkItem *item) {
  if (state_.services.itemKind(*item) != 0 ||
      state_.services.itemFilter(*item) != 0)
    return;
  state_.items.add(item);
  syncListParam(0, state_.items, state_.selected);
}
void NetworkSetupComponent::selectMixer(UC::NetworkItem *item, bool release) {
  if (item == state_.selected)
    return;
  if (state_.selected) {
    if (state_.hasRemoteHandler)
      state_.services.setRemoteMixer(nullptr);
    state_.services.release(*state_.selected, release);
  }
  state_.selected = item;
  if (item) {
    state_.services.acquire(*item);
    auto *client = state_.services.component(*state_.selected);
    void *mixer = client ? state_.services.mixerForClient(*client) : nullptr;
    if (state_.hasRemoteHandler)
      state_.services.setRemoteMixer(mixer);
  }
  Core::CStringBuffer<32> name("None");
  if (state_.selected)
    name = state_.services.itemName(*state_.selected);
  state_.parameters.getParameterByTag(1)->fromString(name, false);
  state_.parameters.getParameterByTag(3)->setValue(state_.selected ? 1.f : 0.f,
                                                   false);
}
void NetworkSetupComponent::paramChanged(Core::Portable::Parameter *parameter,
                                         int message) {
  state_.services.serverParamChanged(parameter, message);
  if (message != Core::Portable::Parameter::kEdit || parameter->getTag() != 2)
    return;
  const int selection =
      static_cast<int>(state_.parameters.getParameterByTag(0)->getValue());
  UC::NetworkItem *item = nullptr;
  if (selection > 0)
    item = state_.items.at(selection - 1);
  selectMixer(item, true);
  if (state_.persistentSelection) {
    Core::CStringBuffer<64> serial(item ? state_.services.itemSerial(*item)
                                        : "");
    state_.persistentSelection->fromString(serial, false);
  }
}
void NetworkSetupComponent::onNetworkShutdown() { selectMixer(nullptr, true); }
void NetworkSetupComponent::checkRestoreMixer() {
  // The original shares this throttle across instances and updates it before
  // checking selection/persistence. The CCL millisecond clock intentionally
  // replaces the legacy raw-nanosecond Core::GetAbsoluteTime division.
  static std::uint64_t lastCheckTicks = 0;
  auto &last = state_.restoreTicks ? *state_.restoreTicks : lastCheckTicks;
  const std::int64_t now = state_.milliseconds
                               ? state_.milliseconds()
                               : Core::SystemClock::getMilliseconds();
  const std::uint64_t thresholdBits = last + 3000;
  std::int64_t threshold;
  std::memcpy(&threshold, &thresholdBits, sizeof(threshold));
  if (now <= threshold)
    return;
  last = static_cast<std::uint64_t>(now);
  if (state_.selected || !state_.persistentSelection)
    return;
  Core::CStringBuffer<64> saved;
  state_.persistentSelection->toString(saved.getBuffer(), 64);
  for (int i = 0; i < state_.items.count(); ++i) {
    UC::NetworkItem *item = state_.items[i];
    if (std::strcmp(saved, state_.services.itemSerial(*item)) == 0) {
      selectMixer(item, true);
      if (state_.hasRemoteHandler)
        state_.services.restoredSelection();
      return;
    }
  }
}
void NetworkSetupComponent::onNetworkItemRemoved(UC::NetworkItem *item) {
  if (item == state_.selected)
    selectMixer(nullptr, false);
  if (state_.services.itemKind(*item) != 0)
    return;
  state_.items.remove(item);
  syncListParam(0, state_.items, state_.selected);
}
void NetworkSetupComponent::syncListParam(
    int tag, const Core::Vector<UC::NetworkItem *> &items,
    UC::NetworkItem *selected) const {
  auto *parameter = static_cast<Core::Portable::ListParam *>(
      state_.parameters.getParameterByTag(tag));
  parameter->removeAll();
  parameter->appendString("None");
  const int count = items.count();
  for (int i = 0; i < count; ++i) {
    Core::CStringBuffer<128> title;
    state_.services.itemTitle(*items[i], title);
    parameter->appendString(title);
  }
  int index = 0;
  if (selected) {
    for (int i = 0; i < items.count(); ++i)
      if (items[i] == selected) {
        index = i + 1;
        break;
      }
  }
  parameter->setValue(static_cast<float>(index), false);
  parameter->rangeChanged();
}
} // namespace Presonus::Mixer
