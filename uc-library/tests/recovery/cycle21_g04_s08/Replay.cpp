#include "presonus/PageComponent.hpp"
#include "presonus/surface/PresetsPageComponent.hpp"
#include "presonus/surface/ScenesPageComponent.hpp"
#include <cstdlib>
#include <iostream>
#include <string_view>

using namespace Core::Portable;
using namespace presonus::surface;
namespace {
struct ObservedParam final : NumericParam {
  explicit ObservedParam(const ParamInfo &info) : NumericParam(info) {}
  ParamValue getValue() const override {
    ++reads;
    return NumericParam::getValue();
  }
  mutable int reads = 0;
};
struct Registry final : Component {
  void adopt(Parameter *parameter) { paramList.add(parameter); }
};
struct Dependencies final : PresetsPageDependencies {
  bool handlerAvailable() override { return true; }
  int count(int category) override {
    if (category != 7)
      std::abort();
    return 4;
  }
  const PresetEntry *preset(int category, int index) override {
    if (category != 7 || index != 2)
      std::abort();
    return &entry;
  }
  void reload(int) override { std::abort(); }
  void defaultName(int, Core::CString128 &) override { std::abort(); }
  void categoryName(int, Core::CString128 &) override { std::abort(); }
  const char *emptyMarker() override { std::abort(); }
  void baseShow(bool) override { std::abort(); }
  bool visible() override { std::abort(); }
  void connect(const char *, Parameter *) override { std::abort(); }
  void recallOptions(Core::CString256 &options) override {
    options = "offline";
  }
  void recall(const PresetEntry *preset, int category,
              const Core::CString256 &options) override {
    if (preset != &entry || category != 7 ||
        std::string_view(options.str()) != "offline")
      std::abort();
    ++calls;
  }
  void remove(const PresetEntry *, int) override { std::abort(); }
  void store() override { std::abort(); }
  void startTextInput(Parameter *, const char *) override { std::abort(); }
  PresetEntry entry{42, "Observed"};
  int calls = 0;
};
struct Bindings final : presonus::page::Bindings {
  Bindings(PresetsPageState &state, Component &component)
      : state(state), component(component) {}
  void *castOwner(void *owner, int type) const override {
    if (type != 1296843588)
      std::abort();
    return owner;
  }
  const void *currentPage(void *) const override {
    selectedAtVisibility = state.selected;
    dirtyAtVisibility = component.needsSave();
    ++visits;
    return visible;
  }
  void stopTextInput(void *, bool) const override { std::abort(); }
  bool isEditingText(void *) const override { return false; }
  PresetsPageState &state;
  Component &component;
  const void *visible = nullptr;
  mutable int visits = 0;
  mutable int selectedAtVisibility = -99;
  mutable int dirtyAtVisibility = -1;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 7)
    return 2;
  const std::string_view mode(argv[1]);
  const bool visible = std::atoi(argv[2]);
  const int message = std::atoi(argv[3]);
  const int kind = std::atoi(argv[4]);
  const float value = std::atoi(argv[5]);
  const bool mixer = std::atoi(argv[6]);

  const ParamInfo foot = PARAM_FLOAT(9, "fsw_load", -8, 8, 0, 0, nullptr,
                                     nullptr, 0, PARAM_STORABLE);
  const ParamInfo other =
      PARAM_FLOAT(9, "other", -8, 8, 0, 0, nullptr, nullptr, 0, PARAM_STORABLE);
  const ParamInfo selection = PARAM_FLOAT(1, "selected", -8, 8, 0, 0, nullptr,
                                          nullptr, 0, PARAM_STORABLE);
  auto *param = new ObservedParam(kind == 0   ? foot
                                  : kind == 1 ? other
                                              : selection);
  param->setValue(value);
  Registry parameters;
  parameters.adopt(param);
  PresetsPageState state{7, 1, 0, 2, mixer, parameters};
  Dependencies dependencies;
  Presonus::Surface::PresetsPageComponent presets(state, dependencies);
  Bindings bindings(state, presets);
  int owner;
  Presonus::PageComponent page(&owner, bindings);
  bindings.visible = visible ? &page : nullptr;
  Core::Vector<Parameter *> extra;
  using Scenes = Presonus::Surface::ScenesPageComponent;
  Scenes scenes(Scenes::SourcePortConstruction{}, extra, &parameters, presets);
  scenes.bindPage(page);
  if (mode == "provider")
    presets.paramChanged(param, message);
  else if (mode == "provider-recall") {
    presets.paramChanged(param, message);
    presets.recall();
  } else if (mode == "scene")
    scenes.paramChanged(param, message);
  else
    return 3;

  std::cout << state.selected << ' ' << presets.needsSave() << ' '
            << param->reads << ' ' << bindings.visits << ' '
            << bindings.selectedAtVisibility << ' '
            << bindings.dirtyAtVisibility << ' ' << dependencies.calls << '\n';
}
