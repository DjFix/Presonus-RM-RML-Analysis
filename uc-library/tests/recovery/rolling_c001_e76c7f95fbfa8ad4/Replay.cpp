#include "presonus/avb/SurfaceAvbComponent.hpp"
#include "presonus/avb/streams.hpp"

#include <cstring>
#include <iostream>
#include <type_traits>

namespace {
class Child final : public Core::Portable::Component {
public:
  explicit Child(bool &destroyed) : destroyed_(destroyed) {}
  ~Child() override { destroyed_ = true; }

private:
  bool &destroyed_;
};
} // namespace

int main() {
  using Presonus::AVB::AvbListener;
  using Presonus::AVB::SurfaceAvbComponent;
  static_assert(
      std::is_same_v<decltype(&SurfaceAvbComponent::handleListenerStateChange),
                     void (SurfaceAvbComponent::*)(AvbListener *)>);
  bool destroyed = false;
  {
    SurfaceAvbComponent receiver;
    AvbListener first(0x12, 0x12345678, 0x1234, -1);
    AvbListener second(0x9a, 0xdecafe, 0x4321, 19);
    auto *child = new Child(destroyed);
    receiver.addChild(child);

    for (AvbListener *listener :
         {static_cast<AvbListener *>(nullptr), &first, &second}) {
      unsigned char receiverBefore[sizeof(receiver)];
      unsigned char listenerBefore[sizeof(first)];
      std::memcpy(receiverBefore, &receiver, sizeof(receiver));
      if (listener)
        std::memcpy(listenerBefore, listener, sizeof(first));

      receiver.handleListenerStateChange(listener);

      const bool receiverUnchanged =
          std::memcmp(receiverBefore, &receiver, sizeof(receiver)) == 0;
      const bool argumentUnchanged =
          !listener ||
          std::memcmp(listenerBefore, listener, sizeof(first)) == 0;
      const bool childRetained = receiver.countChildren() == 1 &&
                                 receiver.getChild(0) == child && !destroyed;
      if (!(receiverUnchanged && argumentUnchanged && childRetained))
        return 1;
      std::cout << "unchanged\n";
    }
  }
  if (!destroyed)
    return 2;
  std::cout << "provider child destroyed\n";
}
