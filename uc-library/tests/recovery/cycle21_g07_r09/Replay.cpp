#include "presonus/surface/PresetsPageComponent.hpp"
#include "presonus/surface/ScenesPageComponent.hpp"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>

using namespace Core::Portable;
using namespace Presonus::Surface;
using namespace presonus::surface;

namespace {
std::uintptr_t extraStorage;
std::uintptr_t aliasStorage;
std::uintptr_t sceneStorage;
std::uintptr_t presetsStorage;
std::uintptr_t *captureArray;
bool report;
bool presetsFreed;

struct Child final : Component {
  ~Child() override {
    if (report)
      std::puts("component child cleanup");
  }
};

struct UnusedPresetServices final : PresetsPageDependencies {
  bool handlerAvailable() override { std::abort(); }
  int count(int) override { std::abort(); }
  const PresetEntry *preset(int, int) override { std::abort(); }
  void reload(int) override { std::abort(); }
  void defaultName(int, Core::CString128 &) override { std::abort(); }
  void categoryName(int, Core::CString128 &) override { std::abort(); }
  const char *emptyMarker() override { std::abort(); }
  void baseShow(bool) override { std::abort(); }
  bool visible() override { std::abort(); }
  void connect(const char *, Parameter *) override { std::abort(); }
  void recallOptions(Core::CString256 &) override { std::abort(); }
  void recall(const PresetEntry *, int, const Core::CString256 &) override {
    std::abort();
  }
  void remove(const PresetEntry *, int) override { std::abort(); }
  void store() override { std::abort(); }
  void startTextInput(Parameter *, const char *) override { std::abort(); }
};

void recordScalar(std::uintptr_t address) {
  if (!report)
    return;
  if (address == presetsStorage)
    presetsFreed = true;
  if (address == sceneStorage)
    std::puts("operator delete");
}
} // namespace

extern "C" void *__real__Znam(std::size_t size);
extern "C" void __real__ZdaPv(void *);
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);

extern "C" void *__wrap__Znam(std::size_t size) {
  void *address = __real__Znam(size);
  if (captureArray)
    *captureArray = reinterpret_cast<std::uintptr_t>(address);
  return address;
}

extern "C" void __wrap__ZdaPv(void *pointer) {
  const auto address = reinterpret_cast<std::uintptr_t>(pointer);
  __real__ZdaPv(pointer);
  if (!report)
    return;
  if (address == extraStorage)
    std::puts("extra vector");
  if (address == aliasStorage)
    std::puts("alias vector");
}

extern "C" void __wrap__ZdlPv(void *pointer) {
  const auto address = reinterpret_cast<std::uintptr_t>(pointer);
  __real__ZdlPv(pointer);
  recordScalar(address);
}

extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  const auto address = reinterpret_cast<std::uintptr_t>(pointer);
  __real__ZdlPvm(pointer, size);
  recordScalar(address);
}

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const bool owned = std::strcmp(argv[1], "owned") == 0;
  ParamInfo paramInfo{};
  paramInfo.type = ParamInfo::kFloat;
  paramInfo.tag = 100;
  NumericParam borrowedParameter(paramInfo);
  ParamInfo aliasInfo{};
  aliasInfo.type = ParamInfo::kAlias;
  aliasInfo.tag = 101;
  AliasParam borrowedAlias(aliasInfo);
  borrowedAlias.setOriginal(&borrowedParameter);
  Core::Vector<Parameter *> external;
  if (!external.add(&borrowedParameter))
    return 3;

  Component parameters;
  PresetsPageState state{.parameters = parameters};
  UnusedPresetServices services;
  auto presets = std::make_unique<PresetsPageComponent>(state, services);
  presetsStorage = reinterpret_cast<std::uintptr_t>(presets.get());
  presets->addChild(new Child);
  captureArray = &aliasStorage;
  const bool addedAlias = presets->portableAliases().add(&borrowedAlias);
  captureArray = nullptr;
  if (!addedAlias || !aliasStorage)
    return 3;

  ScenesPageComponent *scenes = nullptr;
  if (owned) {
    captureArray = &extraStorage;
    scenes = new ScenesPageComponent(ScenesPageComponent::OwnPresetsPage{},
                                     external, &parameters, std::move(presets));
    captureArray = nullptr;
    if (!extraStorage)
      return 3;
  } else {
    ScenesPageComponent simple(ScenesPageComponent::SourcePortConstruction{},
                               external);
    scenes =
        new ScenesPageComponent(ScenesPageComponent::SourcePortConstruction{},
                                external, &parameters, *presets);
  }
  sceneStorage = reinterpret_cast<std::uintptr_t>(scenes);
  report = true;
  delete scenes;
  report = false;
  if (owned != presetsFreed || borrowedParameter.getTag() != 100 ||
      borrowedAlias.getTag() != 101 ||
      borrowedAlias.getOriginal() != &borrowedParameter ||
      external.count() != 1 || external.at(0) != &borrowedParameter)
    return 3;
  if (!owned && (presets->portableAliases().at(0) != &borrowedAlias ||
                 presets->countChildren() != 1))
    return 3;
  std::puts("borrowed entries survived");
}
