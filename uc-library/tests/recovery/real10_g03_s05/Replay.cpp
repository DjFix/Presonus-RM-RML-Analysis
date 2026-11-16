#include "presonus/PageComponent.hpp"
#include "presonus/surface/MainScreenComponent.hpp"
#include "presonus/surface/MappingComponent.hpp"
#include <iostream>
#include <stdexcept>
struct PageBindings : presonus::page::Bindings {
  void *castOwner(void *, int) const override {
    throw std::logic_error("unused");
  }
  const void *currentPage(void *) const override {
    throw std::logic_error("unused");
  }
  void stopTextInput(void *, bool) const override {
    throw std::logic_error("unused");
  }
  bool isEditingText(void *) const override {
    throw std::logic_error("unused");
  }
};
struct App : presonus::mainlcd_port::Application {
  Presonus::PageComponent *findPage(int) const override {
    throw std::logic_error("unused");
  }
  void requestPage(Presonus::PageComponent *) override {
    throw std::logic_error("unused");
  }
  void showNextPage() override { throw std::logic_error("unused"); }
  int startPageTag() const override { throw std::logic_error("unused"); }
  Core::Portable::RootView *rootView(Presonus::LcdView *) const override {
    throw std::logic_error("unused");
  }
  void observeView(Presonus::LcdView *, Presonus::MainLCDComponent &) override {
    throw std::logic_error("unused");
  }
};
using Mapping = Presonus::Surface::MappingComponent;
static int mode = 0, enabled = -1;
extern "C" void realPre(Mapping *, bool) asm(
    "__real__ZN8Presonus7Surface16MappingComponent19setPreampsMeterModeEb");
extern "C" void wrapPre(Mapping *, bool) asm(
    "__wrap__ZN8Presonus7Surface16MappingComponent19setPreampsMeterModeEb");
extern "C" void wrapPre(Mapping *m, bool b) {
  mode = 1;
  enabled = b;
  realPre(m, b);
}
extern "C" void realGeq(Mapping *, bool) asm(
    "__real__ZN8Presonus7Surface16MappingComponent10setGeqModeEb");
extern "C" void wrapGeq(Mapping *, bool) asm(
    "__wrap__ZN8Presonus7Surface16MappingComponent10setGeqModeEb");
extern "C" void wrapGeq(Mapping *m, bool b) {
  mode = 2;
  enabled = b;
  realGeq(m, b);
}
struct MappingReceiver : Mapping {
  MappingReceiver() : Mapping(presonus::surface::MappingRouteInit{}) {}
  bool isDisplayEncoderLocked() const override {
    throw std::logic_error("unused");
  }
  void selectedChannelUpdated() override { throw std::logic_error("unused"); }
};
int main(int argc, char **) {
  PageBindings bindings;
  App app;
  int a, b, previous, bound;
  while (std::cin >> a >> b >> previous >> bound) {
    presonus::mainlcd_port::State state;
    Presonus::Surface::MainScreenComponent screen(
        presonus::surface::MainScreenInit{}, app, state);
    MappingReceiver mapping;
    Core::Portable::ParamInfo infos[4]{};
    for (int i = 0; i < 4; ++i) {
      infos[i].type = Core::Portable::ParamInfo::kFloat;
      infos[i].tag = 34 + i;
      infos[i].maxValue = 1;
      infos[i].defaultValue = 1;
    }
    mapping.addParameters(infos, 4);
    Presonus::PageComponent page(nullptr, bindings), old(nullptr, bindings);
    page.bindObservedPageState(a, 0);
    old.bindObservedPageState(b, 0);
    screen.bindMapping(bound ? &mapping : nullptr);
    mode = 0;
    enabled = -1;
    if (argc > 1) {
      if (a == 1)
        mapping.setPreampsMeterMode(b != 0);
      else if (a == 2)
        mapping.setGeqMode(b != 0);
    } else
      screen.pageAboutToShow(page, previous ? &old : nullptr);
    std::cout << mode << " " << enabled;
    for (int i = 0; i < 4; ++i)
      std::cout << " " << mapping.getParameterByTag(34 + i)->getIntValue();
    std::cout << "\n";
  }
}
