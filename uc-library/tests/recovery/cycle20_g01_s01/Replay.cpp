#include "presonus/surface/MappingComponent.hpp"

#include <array>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>

namespace {
using Mapping = Presonus::Surface::MappingComponent;
using Core::Portable::Attributes;
using Core::Portable::Component;
using Presonus::DelayTimer;
using presonus::mapping::Access;

const void *receiver;
Mapping *mapping;
const DelayTimer *blink;
const DelayTimer *hold;
std::array<const Attributes *, 3> attributes;

void require(bool condition) {
  if (!condition)
    std::abort();
}

class MappingFixture final : public Mapping {
public:
  bool isDisplayEncoderLocked() const override { return false; }
  void selectedChannelUpdated() override {}
};

class HandlerFixture final : public Presonus::AssignmentHandler {
public:
  const char *getName() const override { return "fixture"; }
  void updateConnections() override {}
  void setController(Presonus::IMappingController *controller) override {
    if (!controller) {
      require(controller_ == mapping && !Access::providersUnbound(*mapping));
      std::puts("detach");
    }
    AssignmentHandler::setController(controller);
  }
  bool detached() const { return controller_ == nullptr; }
};
static_assert(sizeof(MappingFixture) == sizeof(Mapping));
static_assert(alignof(MappingFixture) == alignof(Mapping));
} // namespace

extern "C" void
mappingD0(Mapping *) asm("_ZN8Presonus7Surface16MappingComponentD0Ev");
extern "C" void
mappingD1(Mapping *) asm("_ZN8Presonus7Surface16MappingComponentD1Ev");
extern "C" void
mappingD2(Mapping *) asm("_ZN8Presonus7Surface16MappingComponentD2Ev");

extern "C" void realDelete(void *) asm("__real__ZdlPv");
extern "C" void wrappedDelete(void *) asm("__wrap__ZdlPv");
void wrappedDelete(void *pointer) {
  if (pointer == receiver) {
    realDelete(pointer);
    std::puts("delete");
    return;
  }
  realDelete(pointer);
}

extern "C" void
realTimer(DelayTimer *) asm("__real__ZN8Presonus10DelayTimerD1Ev");
extern "C" void
wrappedTimer(DelayTimer *) asm("__wrap__ZN8Presonus10DelayTimerD1Ev");
void wrappedTimer(DelayTimer *timer) {
  if (timer == blink || timer == hold) {
    require(Access::providersUnbound(*mapping));
    std::puts(timer == blink ? "timer:blink" : "timer:hold");
  }
  realTimer(timer);
}

extern "C" void
realAttributes(Attributes *) asm("__real__ZN4Core8Portable10AttributesD2Ev");
extern "C" void
wrappedAttributes(Attributes *) asm("__wrap__ZN4Core8Portable10AttributesD2Ev");
void wrappedAttributes(Attributes *object) {
  for (std::size_t i = 0; i < attributes.size(); ++i) {
    if (object == attributes[i])
      std::printf("attributes:%zu\n", i);
  }
  realAttributes(object);
}

extern "C" void
realComponent(Component *) asm("__real__ZN4Core8Portable9ComponentD2Ev");
extern "C" void
wrappedComponent(Component *) asm("__wrap__ZN4Core8Portable9ComponentD2Ev");
void wrappedComponent(Component *object) {
  if (object == mapping)
    std::puts("component");
  realComponent(object);
}

int main(int argc, char **argv) {
  require(argc == 3);
  const bool deleting = std::strcmp(argv[1], "D0") == 0;
  const bool bound = std::strcmp(argv[2], "bound") == 0;
  alignas(MappingFixture) std::byte storage[sizeof(MappingFixture)];
  auto *fixture =
      deleting ? new MappingFixture : ::new (storage) MappingFixture;
  mapping = fixture;
  require(static_cast<void *>(fixture) == static_cast<void *>(mapping));
  receiver = mapping;
  blink = &Access::blink(*mapping);
  hold = &Access::hold(*mapping);
  auto &lists = Access::constructorAttributes(*mapping);
  require(lists.has_value());
  for (std::size_t i = 0; i < attributes.size(); ++i)
    attributes[i] = &(*lists)[i];

  HandlerFixture handler;
  if (bound) {
    handler.setController(mapping);
    Access::bindAssignmentHandler(*mapping, &handler);
  }
  if (deleting)
    mappingD0(mapping);
  else if (std::strcmp(argv[1], "D1") == 0)
    mappingD1(mapping);
  else {
    require(std::strcmp(argv[1], "D2") == 0);
    mappingD2(mapping);
  }
  require(handler.detached());
}
