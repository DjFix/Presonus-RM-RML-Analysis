#include "presonus/surface/MappingComponent.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <iostream>
#include <stdexcept>
#include <string>

using namespace Core::Portable;
using namespace Presonus::Surface;

namespace {
struct Observer : ParamObserverBase {
  void paramChanged(Parameter *, int) override { ++called; }
  int called = 0;
};

struct PageParam : NumericParam {
  using NumericParam::NumericParam;
  int observers() const { return observerList.count(); }
  void setValue(ParamValue value, bool edit) override {
    std::cout << "set " << static_cast<int>(value) << ' ' << edit << ' '
              << observers() << '\n';
    NumericParam::setValue(value, edit);
  }
};

struct Screen : Component {
  Screen() : Component("mainscreen") {}
  void attach(PageParam *page) { paramList.add(page); }
};

struct Mapping : MappingComponent {
  Mapping() : MappingComponent(presonus::surface::MappingRouteInit{}) {
    setName("mapping");
  }
  bool isDisplayEncoderLocked() const override { std::abort(); }
  void selectedChannelUpdated() override { std::abort(); }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const bool present = std::stoi(argv[1]) != 0;
  const int flags = std::stoi(argv[2]);
  static const ParamInfo pageInfo =
      PARAM_INT(31, "diagnostics", 0, 10, 0, 0, 0, 0, 0);
  static const ParamInfo mappingInfo[] = {PARAM_TOGGLE(9, "first", 0, 0, 0),
                                          PARAM_TOGGLE(10, "second", 0, 0, 0),
                                          PARAM_TOGGLE(8, "third", 0, 0, 0)};
  Observer observer;
  Component tree("root");
  auto *screen = new Screen;
  auto *page = new PageParam(pageInfo);
  screen->attach(page);
  tree.addChild(screen);
  presonus::surface::RootServices services;
  services.children = &tree;
  services.observer = &observer;
  services.mainScreens.push_back(
      {screen, reinterpret_cast<MainScreenComponent *>(std::uintptr_t{0x1234}),
       "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0",
       "_ZTIN8Presonus7Surface19MainScreenComponentE", 0x1a0434});
  if (present) {
    auto *mapping = new Mapping;
    mapping->addParameters(mappingInfo, 3);
    for (int i = 0; i < 3; ++i)
      mapping->getParameterByTag(mappingInfo[i].tag)
          ->setValue((flags >> i) & 1);
    tree.addChild(mapping);
    services.mappingComponents.push_back(mapping);
  }
  SurfaceRootComponent root;
  root.bindServices(services);
  root.paramChangedDiagnositcsPage();
  std::cout << "state " << static_cast<int>(page->getValue()) << ' '
            << page->observers() << ' ' << observer.called << '\n';
  page->removeObserver(&observer);
}
