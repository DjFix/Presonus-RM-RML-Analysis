#include "presonus/DAWChannelGroup.hpp"

#include <cassert>
#include <cstddef>
#include <cstring>
#include <iostream>
#include <new>
#include <string_view>

using Core::Portable::Component;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Core::Portable::ParamObserverBase;
using Presonus::DAWChannelGroup;

extern "C" void
constructComplete(DAWChannelGroup *) asm("_ZN8Presonus15DAWChannelGroupC1Ev");
extern "C" void
constructBase(DAWChannelGroup *) asm("_ZN8Presonus15DAWChannelGroupC2Ev");
extern "C" void
destroyComplete(DAWChannelGroup *) asm("_ZN8Presonus15DAWChannelGroupD1Ev");
extern "C" void
destroyDeleting(DAWChannelGroup *) asm("_ZN8Presonus15DAWChannelGroupD0Ev");

namespace {
struct MemberProbe : DAWChannelGroup {
  static constexpr auto cachedParameter = &MemberProbe::cachedParameter_;
};

void *receiver{};
bool childDestroyed{};
bool parameterDestroyed{};
bool receiverFreed{};

struct Child : Component {
  ~Child() override {
    assert(!childDestroyed && !receiverFreed);
    childDestroyed = true;
  }
};

struct Observer : ParamObserverBase {
  void paramChanged(Parameter *, int message) override {
    assert(message == Parameter::kDestroyed);
    assert(childDestroyed && !parameterDestroyed && !receiverFreed);
    parameterDestroyed = true;
  }
};

void verifyConstruction(DAWChannelGroup &object) {
  assert(std::string_view(object.getName()).empty());
  assert(object.getParent() == nullptr);
  assert(object.countChildren() == 0 && object.countParameters() == 0);
  assert(object.*MemberProbe::cachedParameter == nullptr);
  const Component *base = &object;
  assert(typeid(*base) == typeid(DAWChannelGroup));
}
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *ptr) {
  if (ptr == receiver) {
    assert(childDestroyed && parameterDestroyed && !receiverFreed);
    receiverFreed = true;
  }
  __real__ZdlPv(ptr);
}

extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPvm(void *ptr, std::size_t size) {
  assert(ptr != receiver);
  __real__ZdlPvm(ptr, size);
}

int main(int argc, char **argv) {
  assert(argc == 2);
  const std::string_view variant = argv[1];
  unsigned sentinel;
  int typeId;
  while (std::cin >> sentinel >> typeId) {
    alignas(DAWChannelGroup) std::byte storage[sizeof(DAWChannelGroup)];
    const bool deleting = variant == "D0";
    void *memory = deleting ? ::operator new(sizeof(DAWChannelGroup)) : storage;
    std::memset(memory, sentinel, sizeof(DAWChannelGroup));
    auto *object = static_cast<DAWChannelGroup *>(memory);
    if (variant == "C2")
      constructBase(object);
    else
      constructComplete(object);
    object = std::launder(object);
    verifyConstruction(*object);
    if (variant == "C1" || variant == "C2") {
      destroyComplete(object);
      std::cout << "client_construct empty cached_null\n";
    } else if (variant == "cast") {
      Component *component = object;
      const auto castResult = component->castTo(typeId);
      assert(castResult == nullptr || castResult == object);
      std::cout << (castResult == object ? "receiver\n" : "null\n");
      destroyComplete(object);
    } else {
      assert(variant == "D1" || deleting);
      Observer observer;
      const ParamInfo info = PARAM_TOGGLE(7, "observed", 0, nullptr, 0);
      object->addChild(new Child);
      object->addParameters(&info, 1);
      assert(object->countChildren() == 1 && object->countParameters() == 1);
      object->getParameterAt(0)->addObserver(&observer);
      childDestroyed = parameterDestroyed = receiverFreed = false;
      receiver = object;
      if (deleting)
        destroyDeleting(object);
      else
        destroyComplete(object);
      assert(childDestroyed && parameterDestroyed && receiverFreed == deleting);
      receiver = nullptr;
      std::cout << (deleting ? "component_destroy delete\n"
                             : "component_destroy\n");
    }
  }
  assert(std::cin.eof());
}
