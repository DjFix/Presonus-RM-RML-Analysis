#include "presonus/surface/GeqPresetsPageComponent.hpp"
#include <cstdlib>
#include <iostream>
#include <string_view>

using namespace Presonus::Surface;
using namespace presonus::surface;
using namespace Core::Portable;

struct Dependencies : PresetsPageDependencies {
  bool handlerAvailable() override { return false; }
  int count(int) override { return 0; }
  const PresetEntry *preset(int, int) override { return nullptr; }
  void reload(int) override {}
  void defaultName(int, Core::CString128 &) override {}
  void categoryName(int, Core::CString128 &) override {}
  const char *emptyMarker() override { return ""; }
  void baseShow(bool) override {}
  bool visible() override { return false; }
  void connect(const char *, Parameter *) override {}
  void recallOptions(Core::CString256 &) override {}
  void recall(const PresetEntry *, int, const Core::CString256 &) override {}
  void remove(const PresetEntry *, int) override {}
  void store() override {}
  void startTextInput(Parameter *, const char *) override {}
};

int main(int argc, char **argv) {
  if (argc != 6)
    return 2;
  const bool hasParameter = std::atoi(argv[1]);
  const float value = std::strtof(argv[2], nullptr);
  const int count = std::atoi(argv[3]);
  const int omitted = std::atoi(argv[4]);
  const std::string_view mode(argv[5]);
  const ParamInfo infos[] = {
      PARAM_FLOAT(15, "selected_mix", 0, 30, 0, 0.01f, 0, 0, 0, 0)};
  Component root("root"), parameters("parameters");
  PresetsPageState state{.parameters = parameters};
  Dependencies dependencies;
  Core::Vector<Component *> mixes;
  for (int index = 0; index < count; ++index) {
    Core::CString32 name;
    name.appendFormat("Mix%d", index);
    auto *component = new Component(name);
    root.addChild(component);
    mixes.add(index == omitted ? nullptr : component);
  }
  auto *main = new Component("Main");
  auto *alternate = new Component("Alternate");
  root.addChild(main);
  root.addChild(alternate);
  GeqPresetTargets targets{mixes, omitted == 20 ? nullptr : main,
                           omitted == 21 ? nullptr : alternate};
  GeqPresetsPageComponent page(state, dependencies, targets);
  if (hasParameter) {
    page.addParameters(infos, 1);
    page.findParameter("selected_mix")->setValue(value, false);
  }
  Core::CString256 out("unchanged");
  if (mode == "page") {
    page.getTargetUrl(out);
  } else {
    auto *child = root.findChild(argv[5]);
    if (!child)
      return 3;
    child->getComponentPath(out);
  }
  std::cout << out.str() << '\n';
}
