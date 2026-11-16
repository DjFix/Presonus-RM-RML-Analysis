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
struct PageChild : Core::Portable::Component {
  Presonus::PageComponent page;
  bool casts;
  PageChild(PageBindings &b, int tag, bool c) : page(nullptr, b), casts(c) {
    page.bindObservedPageState(tag, 0);
  }
  void *castTo(int type) override {
    return casts && type == 1348560741 ? &page : nullptr;
  }
};
int main(int argc, char **) {
  PageBindings bindings;
  int n, q, mask, a, b, c;
  while (std::cin >> n >> q >> mask >> a >> b >> c) {
    App app;
    presonus::mainlcd_port::State state;
    Presonus::MainLCDComponent screen(app, state);
    int tags[] = {a, b, c};
    PageChild *children[3]{};
    for (int i = 0; i < n; ++i) {
      children[i] = new PageChild(bindings, tags[i], mask & (1 << i));
      screen.addChild(children[i]);
    }
    if (argc > 1) {
      for (int i = 0; i < n; ++i)
        std::cout << (children[i]->castTo(1348560741) != nullptr) << " "
                  << children[i]->page.getPageTag() << " ";
      std::cout << "\n";
    } else {
      auto *result = screen.getPageByTag(q);
      int index = -1;
      for (int i = 0; i < n; ++i)
        if (result == &children[i]->page)
          index = i;
      std::cout << index << "\n";
    }
  }
}
