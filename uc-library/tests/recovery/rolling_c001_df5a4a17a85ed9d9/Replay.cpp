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
  using Presonus::AVB::AvbTalker;
  using Presonus::AVB::SurfaceAvbComponent;
  static_assert(
      std::is_same_v<decltype(&SurfaceAvbComponent::handleTalkerStateChange),
                     void (SurfaceAvbComponent::*)(AvbTalker *)>);
  bool destroyed = false;
  {
    SurfaceAvbComponent receiver;
    AvbTalker first(0x12, 0x12345678);
    AvbTalker second(0x9a, -1);
    auto *child = new Child(destroyed);
    receiver.addChild(child);

    for (AvbTalker *talker :
         {static_cast<AvbTalker *>(nullptr), &first, &second}) {
      unsigned char receiverBefore[sizeof(receiver)];
      unsigned char talkerBefore[sizeof(first)];
      std::memcpy(receiverBefore, &receiver, sizeof(receiver));
      if (talker)
        std::memcpy(talkerBefore, talker, sizeof(first));

      receiver.handleTalkerStateChange(talker);

      const bool receiverUnchanged =
          std::memcmp(receiverBefore, &receiver, sizeof(receiver)) == 0;
      const bool argumentUnchanged =
          !talker || std::memcmp(talkerBefore, talker, sizeof(first)) == 0;
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
