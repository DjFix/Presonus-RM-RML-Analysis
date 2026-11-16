#include "presonus/surface/PresetsPageComponent.hpp"
#include "presonus/surface/ScenesPageComponent.hpp"
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
struct Value : Core::Portable::NumericParam {
  explicit Value(const Core::Portable::ParamInfo &info) : NumericParam(info) {}
  float value = 0;
  float getValue() const override { return value; }
};
struct Dependencies : presonus::surface::PresetsPageDependencies {
  int scenario = 0, recalls = 0, options = 0;
  presonus::surface::PresetEntry entry{42, "Scene"};
  bool handlerAvailable() override { return scenario != 2; }
  int count(int) override { return 3; }
  const presonus::surface::PresetEntry *preset(int, int) override {
    return scenario == 5 ? nullptr : &entry;
  }
  void recallOptions(Core::CString256 &out) override {
    ++options;
    out = "bounded-options";
  }
  void recall(const presonus::surface::PresetEntry *p, int category,
              const Core::CString256 &opts) override {
    if (p != &entry || category != 7 ||
        std::strcmp(opts.str(), "bounded-options"))
      std::abort();
    ++recalls;
  }
  void reload(int) override { std::abort(); }
  void defaultName(int, Core::CString128 &) override { std::abort(); }
  void categoryName(int, Core::CString128 &) override { std::abort(); }
  const char *emptyMarker() override { std::abort(); }
  void baseShow(bool) override { std::abort(); }
  bool visible() override { std::abort(); }
  void connect(const char *, Core::Portable::Parameter *) override {
    std::abort();
  }
  void remove(const presonus::surface::PresetEntry *, int) override {
    std::abort();
  }
  void store() override { std::abort(); }
  void startTextInput(Core::Portable::Parameter *, const char *) override {
    std::abort();
  }
};
int main() {
  int provider, parameter;
  std::uint32_t bits;
  while (std::cin >> provider >> parameter >> bits)
    for (int scenario = 0; scenario < 6; ++scenario) {
      Core::Vector<Core::Portable::Parameter *> extra;
      Core::Portable::Component source;
      Core::Portable::ParamInfo info = PARAM_ALIAS(12, "selected", 0);
      if (parameter)
        source.addParameters(&info, 1);
      auto *p = source.getParameterByTag(12);
      Core::Portable::ParamInfo valueInfo{};
      Value value(valueInfo);
      std::memcpy(&value.value, &bits, 4);
      if (p)
        Core::Portable::AliasParam::cast(p)->setOriginal(&value);
      Dependencies deps;
      deps.scenario = scenario;
      presonus::surface::PresetsPageState state{
          7,
          1,
          0,
          scenario == 3 ? -1 : scenario == 4 ? 9 : 1,
          scenario != 1,
          source};
      Presonus::Surface::PresetsPageComponent presets(state, deps);
      Presonus::Surface::ScenesPageComponent c(
          Presonus::Surface::ScenesPageComponent::SourcePortConstruction{},
          extra, provider ? &source : nullptr, presets);
      const float observed = p ? p->getValue() : 0.f;
      std::uint32_t observedBits;
      std::memcpy(&observedBits, &observed, 4);
      presets.recall();
      const int baselineRecalls = deps.recalls, baselineOptions = deps.options;
      deps.recalls = deps.options = 0;
      c.rowSelected();
      std::cout << scenario << " " << baselineRecalls << " " << baselineOptions
                << " " << deps.recalls << " " << deps.options << " "
                << observedBits << "\n";
      if (p)
        Core::Portable::AliasParam::cast(p)->setOriginal(nullptr);
    }
}
