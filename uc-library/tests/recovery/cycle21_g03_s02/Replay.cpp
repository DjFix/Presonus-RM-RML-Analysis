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
  void baseShow(bool show) override { std::cout << "base " << show << '\n'; }
  bool visible() override { return false; }
  void connect(const char *name, Parameter *parameter) override {
    std::cout << name << ' ' << (parameter ? parameter->getTag() : -1) << '\n';
  }
  void recallOptions(Core::CString256 &) override {}
  void recall(const PresetEntry *, int, const Core::CString256 &) override {}
  void remove(const PresetEntry *, int) override {}
  void store() override {}
  void startTextInput(Parameter *, const char *) override {}
};

struct Observer final : ParamObserverBase {
  void paramChanged(Parameter *parameter, int message) override {
    char title[64]{};
    parameter->toString(title, sizeof(title));
    std::cout << "observe " << parameter->getTag() << ' ' << message << ' '
              << title << '\n';
  }
};

int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  const bool show = std::atoi(argv[1]);
  const bool hasParameter = std::atoi(argv[2]);
  const bool directBase = std::string_view(argv[3]) == "base";
  const ParamInfo titleInfo = PARAM_STRING(1007, "title", 0);
  Component parameters;
  PresetsPageState state{.parameters = parameters};
  Dependencies dependencies;
  GeqPresetsPageComponent page(state, dependencies);
  Observer observer;
  Parameter *title = nullptr;
  if (hasParameter) {
    page.addParameters(&titleInfo, 1);
    title = page.getParameterByTag(1007);
    title->fromString("before", false);
    title->addObserver(&observer);
  }
  if (directBase)
    page.PresetsPageComponent::onShow(show);
  else
    page.onShow(show);
  if (title) {
    char text[64]{};
    title->toString(text, sizeof(text));
    std::cout << "final " << text << '\n';
    title->removeObserver(&observer);
  }
}
