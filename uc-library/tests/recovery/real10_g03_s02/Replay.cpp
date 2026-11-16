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
  Presonus::PageComponent *result = nullptr;
  int requests = 0;
  Presonus::PageComponent *findPage(int tag) const override {
    if (tag != 0)
      throw std::logic_error("wrong start");
    return result;
  }
  void requestPage(Presonus::PageComponent *p) override {
    if (p != result)
      throw std::logic_error("wrong page");
    ++requests;
  }
  void showNextPage() override { throw std::logic_error("unused"); }
  int startPageTag() const override { return 101; }
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
  int a, has;
  while (std::cin >> a >> has) {
    Presonus::PageComponent page(nullptr, bindings), start(nullptr, bindings);
    page.bindObservedPageState(a, 0);
    app.result = &start;
    app.requests = 0;
    state.current = has ? &page : nullptr;
    if (argc > 1)
      std::cout << screen.getCurrentPageTag() << "\n";
    else {
      screen.onSelectedChannelChanged();
      std::cout << app.requests << "\n";
    }
  }
}
