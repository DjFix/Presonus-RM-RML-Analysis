#include "presonus/surface/ChannelPresetsPageComponent.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>
#include <stdexcept>
namespace {
void *objectAddress = nullptr, *vectorAddress = nullptr;
int objectFrees = 0, vectorFrees = 0, childDestructions = 0,
    aliasDestructions = 0;
void observedDelete(void *p) {
  if (p == objectAddress)
    ++objectFrees;
  if (p == vectorAddress)
    ++vectorFrees;
  std::free(p);
}
struct Child final : Core::Portable::Component {
  ~Child() override { ++childDestructions; }
};
struct Alias final : Core::Portable::AliasParam {
  Alias(const Core::Portable::ParamInfo &p) : AliasParam(p) {}
  ~Alias() override { ++aliasDestructions; }
};
// Test boundary only. A lifecycle must never call application services.
struct Dependencies final : presonus::surface::PresetsPageDependencies {
  bool handlerAvailable() override { throw 1; }
  int count(int) override { throw 1; }
  const presonus::surface::PresetEntry *preset(int, int) override { throw 1; }
  void reload(int) override { throw 1; }
  void defaultName(int, Core::CString128 &) override { throw 1; }
  void categoryName(int, Core::CString128 &) override { throw 1; }
  const char *emptyMarker() override { throw 1; }
  void baseShow(bool) override { throw 1; }
  bool visible() override { throw 1; }
  void connect(const char *, Core::Portable::Parameter *) override { throw 1; }
  void recallOptions(Core::CString256 &) override { throw 1; }
  void recall(const presonus::surface::PresetEntry *, int,
              const Core::CString256 &) override {
    throw 1;
  }
  void remove(const presonus::surface::PresetEntry *, int) override { throw 1; }
  void store() override { throw 1; }
  void startTextInput(Core::Portable::Parameter *, const char *) override {
    throw 1;
  }
};
} // namespace
void operator delete(void *p) noexcept { observedDelete(p); }
void operator delete(void *p, std::size_t) noexcept { observedDelete(p); }
void operator delete[](void *p) noexcept { observedDelete(p); }
void operator delete[](void *p, std::size_t) noexcept { observedDelete(p); }
extern "C" void originalVariant(void *) asm(
    "_ZN8Presonus7Surface27ChannelPresetsPageComponentD1Ev");
int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  const bool provider = std::strcmp(argv[1], "provider") == 0;
  int count = std::atoi(argv[2]), children = std::atoi(argv[3]);
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kAlias;
  Alias borrowed(info);
  Core::Portable::Component parameters;
  presonus::surface::PresetsPageState state{0, 1, 0, -1, false, parameters};
  Dependencies dependencies;
  bool nondeleting = true;
  if (provider) {
    void *storage = ::operator new(sizeof(Core::Portable::Component));
    auto *component = new (storage) Core::Portable::Component;
    objectAddress = component;
    for (int j = 0; j < children; ++j)
      component->addChild(new Child);
    {
      Core::Vector<Core::Portable::AliasParam *> aliases;
      for (int j = 0; j < count; ++j)
        aliases.add(&borrowed);
      vectorAddress = aliases.getItems();
    }
    component->~Component();
    if (!nondeleting)
      ::operator delete(component);
    if (nondeleting)
      std::free(storage);
  } else {
    void *storage =
        ::operator new(sizeof(Presonus::Surface::ChannelPresetsPageComponent));
    auto *component = new (storage)
        Presonus::Surface::ChannelPresetsPageComponent(state, dependencies);
    objectAddress = component;
    for (int j = 0; j < children; ++j)
      component->addChild(new Child);
    for (int j = 0; j < count; ++j)
      component->portableAliases().add(&borrowed);
    vectorAddress = component->portableAliases().getItems();
    originalVariant(component);
    if (nondeleting)
      std::free(storage);
  }
  // Real allocator callbacks and real child destructors, never synthetic
  // events.
  std::printf("%d %d %d %d\n", vectorFrees, objectFrees, childDestructions,
              aliasDestructions);
  objectAddress = nullptr;
  vectorAddress = nullptr;
  return 0;
}
