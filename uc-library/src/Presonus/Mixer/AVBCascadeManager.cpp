#include "presonus/mixer/AVBCascadeManager.hpp"
namespace Presonus::Mixer {
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
