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
  int startTag = 101;
  Presonus::PageComponent *findPage(int tag) const override {
    if (tag != 101)
      throw std::logic_error("wrong start");
    return result;
  }
  void requestPage(Presonus::PageComponent *p) override {
    if (p != result)
      throw std::logic_error("wrong page");
    ++requests;
  }
  void showNextPage() override { throw std::logic_error("unused"); }
  int startPageTag() const override { return startTag; }
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
  int a, b, has;
  while (std::cin >> a >> b >> has) {
    Presonus::PageComponent page(nullptr, bindings);
    page.bindObservedPageState(a, 0);
    app.startTag = b;
    state.current = has ? &page : nullptr;
    if (argc > 1)
      std::cout << screen.getCurrentPageTag() << " " << screen.getStartPageTag()
                << "\n";
    else
      std::cout << screen.displayEncoderAssignmentLocked() << "\n";
  }
}
