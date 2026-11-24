#include "presonus/mixer/AVBCascadeManager.hpp"
#include "presonus/uc/NetworkItem.hpp"

#include <cstring>
#include <iostream>
#include <type_traits>

namespace {
using Presonus::UC::NetworkItem;
class Boundary final : public presonus::mixer::CascadeBoundary {
public:
  void select(NetworkItem *, bool) override { ++calls; }
  bool connectedClientPresent() override {
    ++calls;
    return false;
  }
  void connectionChanged(bool) override { ++calls; }
  void updateChannelSelectionSync() override { ++calls; }
  unsigned calls = 0;
};
} // namespace

int main() {
  using Presonus::Mixer::AVBCascadeManager;
  static_assert(
      std::is_same_v<decltype(&AVBCascadeManager::onNetworkItemReleased),
                     void (AVBCascadeManager::*)(NetworkItem *)>);
  Boundary boundary;
  int firstComponent = 120;
  int secondComponent = 241;
  NetworkItem first(&firstComponent);
  NetworkItem second(&secondComponent);
  {
    AVBCascadeManager receiver(boundary, &first);
    for (NetworkItem *item :
         {static_cast<NetworkItem *>(nullptr), &first, &second}) {
      unsigned char receiverBefore[sizeof(receiver)];
      unsigned char argumentBefore[sizeof(first)];
      std::memcpy(receiverBefore, &receiver, sizeof(receiver));
      if (item)
        std::memcpy(argumentBefore, item, sizeof(first));

      receiver.onNetworkItemReleased(item);

      if (std::memcmp(receiverBefore, &receiver, sizeof(receiver)) ||
          (item && std::memcmp(argumentBefore, item, sizeof(first))) ||
          boundary.calls || !receiver.isConnected(&first) ||
          receiver.isConnected(&second) ||
          first.getComponent() != &firstComponent ||
          second.getComponent() != &secondComponent || firstComponent != 120 ||
          secondComponent != 241)
        return 1;
      std::cout << "unchanged\n";
    }
  }
  if (boundary.calls)
    return 2;
  std::cout << "portable receiver lifecycle completed\n";
}
