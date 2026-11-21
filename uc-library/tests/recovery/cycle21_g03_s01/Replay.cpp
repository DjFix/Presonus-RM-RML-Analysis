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

template <class Page> struct Probe : Page {
  using Page::Page;
  int rowsSelected = 0;
  void rowSelected() override { ++rowsSelected; }
};

template <class Page> void exercise(int message) {
  const ParamInfo infos[] = {PARAM_TOGGLE(1, "row", 0, 0, 0)};
  Component parameters;
  parameters.addParameters(infos, 1);
  PresetsPageState state{.offset = 7, .parameters = parameters};
  Dependencies dependencies;
  Probe<Page> page(state, dependencies);
  auto *param = parameters.getParameterByTag(1);
  param->setValue(1, false);
  static_cast<Component &>(page).paramChanged(param, message);
  std::cout << state.selected << ' ' << page.rowsSelected << ' '
            << param->getValue() << '\n';
}

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const int message = std::atoi(argv[2]);
  if (std::string_view(argv[1]) == "derived")
    exercise<GeqPresetsPageComponent>(message);
  else
    exercise<PresetsPageComponent>(message);
}
