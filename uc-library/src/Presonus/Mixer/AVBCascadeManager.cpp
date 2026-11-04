#include "presonus/mixer/AVBCascadeManager.hpp"
#include "presonus/uc/NetworkItem.hpp"
namespace Presonus::Mixer {
std::uint32_t AVBCascadeManager::getSlaveId() const {
  if (!selected_ || !selected_->getComponent())
    return 0;
  const void *component = selected_->getComponent();
  for (const auto &entry : componentIds_)
    if (entry.component == component && entry.borrowedId)
      return *entry.borrowedId;
  // Missing source-port state is an explicit integration error, not native
  // zero.
  throw std::logic_error("unbound cascade component ID source state");
}

void AVBCascadeManager::connect(UC::NetworkItem *item) {
  boundary_.select(item, true);
}
void AVBCascadeManager::onNetworkShutdown() { boundary_.select(nullptr, true); }
bool AVBCascadeManager::isConnected(UC::NetworkItem *item) const {
  return selected_ == item;
}
void AVBCascadeManager::onNetworkItemRemoved(UC::NetworkItem *item) {
  if (selected_ == item)
    boundary_.select(nullptr, false);
}
void AVBCascadeManager::cardConnectionChanged(bool connected) {
  cardConnected_ = connected;
  const bool present = boundary_.connectedClientPresent();
  boundary_.connectionChanged(present);
  boundary_.updateChannelSelectionSync();
}
} // namespace Presonus::Mixer
