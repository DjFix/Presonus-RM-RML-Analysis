#include "presonus/surface/SoloPageComponent.hpp"
#include <cstdio>
#include <cstring>
#include <new>

using Core::Portable::AliasParam;
using Core::Portable::Component;
using Core::Portable::ParamInfo;
using Presonus::Surface::SoloPageComponent;

namespace {
void *receiver;
void *vectorStorage;
bool recordArray;
bool vectorReleased;
bool receiverReleased;
bool childDestroyed;

class Child final : public Component {
public:
  ~Child() override { childDestroyed = true; }
};
} // namespace

extern "C" void *__real__Znam(std::size_t size);
extern "C" void __real__ZdaPv(void *ptr);
extern "C" void __real__ZdlPvm(void *ptr, std::size_t size);
extern "C" void __real__ZdlPv(void *ptr);

extern "C" void *__wrap__Znam(std::size_t size) {
  auto *ptr = __real__Znam(size);
  if (recordArray)
    vectorStorage = ptr;
  return ptr;
}
extern "C" void __wrap__ZdaPv(void *ptr) {
  __real__ZdaPv(ptr);
  if (ptr == vectorStorage)
    vectorReleased = true;
}
extern "C" void __wrap__ZdlPvm(void *ptr, std::size_t size) {
  __real__ZdlPvm(ptr, size);
  if (ptr == receiver)
    receiverReleased = true;
}
extern "C" void __wrap__ZdlPv(void *ptr) {
  __real__ZdlPv(ptr);
  if (ptr == receiver)
    receiverReleased = true;
}

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  ParamInfo info{};
  info.tag = 73;
  AliasParam alias(info);
  alignas(SoloPageComponent) unsigned char storage[sizeof(SoloPageComponent)];
  const bool deleting = std::strcmp(argv[1], "D0") == 0;
  auto *component =
      deleting ? new SoloPageComponent : new (storage) SoloPageComponent;
  receiver = component;
  component->addChild(new Child);
  recordArray = true;
  const bool added = component->addAliasReference(alias);
  recordArray = false;
  if (!added || !vectorStorage)
    return 3;
  if (deleting) {
    Component *base = component;
    delete base;
  } else {
    component->~SoloPageComponent();
  }
  std::printf("%d %d %d %d\n", vectorReleased, childDestroyed, receiverReleased,
              alias.getTag() == 73);
}
