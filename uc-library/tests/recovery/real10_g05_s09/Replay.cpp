#include "presonus/mixer/ChannelDCAComponent.hpp"
#include <cstdlib>
#include <iostream>
#include <new>
using Presonus::Mixer::ChannelDCAComponent;
namespace {
void *receiver = nullptr;
void *storage = nullptr;
int receiverDeletes = 0, storageDeletes = 0, childrenDestroyed = 0;
int order = 0, vectorOrder = 0, childOrder = 0, deleteOrder = 0;
} // namespace
void operator delete(void *p) noexcept {
  if (p == receiver) {
    ++receiverDeletes;
    deleteOrder = ++order;
  }
  if (p == storage) {
    ++storageDeletes;
    vectorOrder = ++order;
  }
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
void operator delete[](void *p) noexcept {
  if (p == storage) {
    ++storageDeletes;
    vectorOrder = ++order;
  }
  std::free(p);
}
void operator delete[](void *p, std::size_t) noexcept {
  ::operator delete[](p);
}
class Child : public Core::Portable::Component {
public:
  ~Child() override {
    ++childrenDestroyed;
    childOrder = ++order;
  }
};
extern "C" void selectedDestructor(ChannelDCAComponent *) asm(
    "_ZN8Presonus5Mixer19ChannelDCAComponentD0Ev");
int main() {
  for (int count : {0, 1, 8}) {
    receiverDeletes = storageDeletes = childrenDestroyed = 0;
    order = vectorOrder = childOrder = deleteOrder = 0;
    auto *c =
        new ChannelDCAComponent(ChannelDCAComponent::SourcePortConstruction{});
    receiver = c;
    int borrowed = 12345;
    for (int i = 0; i < count; ++i)
      c->sourcePortHandlers().add(
          reinterpret_cast<Presonus::Mixer::DCALevelHandler *>(&borrowed));
    storage = c->sourcePortHandlers().getItems();
    c->addChild(new Child);
    selectedDestructor(c);
    if ((count && !(vectorOrder < childOrder)) ||
        (1 && !(childOrder < deleteOrder)))
      return 4;
    if (childrenDestroyed != 1 || storageDeletes != (count ? 1 : 0) ||
        receiverDeletes != 1 || borrowed != 12345)
      return 1;
    std::cout << count << " " << childrenDestroyed << " " << storageDeletes
              << " " << receiverDeletes << " " << borrowed << "\n";
    if (!1) {
      receiver = nullptr;
      ::operator delete(c);
    }
    receiver = storage = nullptr;
  }
  {
    Core::Vector<int *> v;
    int value = 17;
    v.add(&value);
    storage = v.getItems();
    storageDeletes = 0;
    v.resize(0);
    if (storageDeletes != 1 || value != 17)
      return 2;
    storage = nullptr;
  }
  childrenDestroyed = 0;
  {
    Core::Portable::Component c;
    c.addChild(new Child);
  }
  if (childrenDestroyed != 1)
    return 3;
}
