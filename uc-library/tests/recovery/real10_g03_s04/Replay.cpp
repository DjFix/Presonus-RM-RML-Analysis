#include "presonus/PageComponent.hpp"
#include "presonus/surface/MainScreenComponent.hpp"
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
int main(int argc, char **) {
  PageBindings bindings;
  App app;
  presonus::mainlcd_port::State state;
  Presonus::Surface::MainScreenComponent screen(
      presonus::surface::MainScreenInit{}, app, state);
  int a, b;
  while (std::cin >> a >> b) {
    Presonus::PageComponent from(nullptr, bindings), to(nullptr, bindings);
    from.bindObservedPageState(a, 0);
    to.bindObservedPageState(b, 0);
    if (argc > 1)
      std::cout << from.getPageTag() << " " << to.getPageTag() << "\n";
    else
      std::cout << screen.canGoBack(from, to) << "\n";
  }
}
