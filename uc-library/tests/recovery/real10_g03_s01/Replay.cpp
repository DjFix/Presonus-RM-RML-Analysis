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
static void *tracked = nullptr;
static int deletes = 0, cleaned = 0;
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == tracked)
    ++deletes;
  __real__ZdlPv(p);
}
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  if (p == tracked)
    ++deletes;
  __real__ZdlPvm(p, n);
}
struct Child : Core::Portable::Component {
  ~Child() override { ++cleaned; }
};
int main(int argc, char **) {
  int count, linked, n;
  while (std::cin >> count >> linked >> n) {
    PageBindings bindings;
    App app;
    Presonus::PageComponent borrowed(nullptr, bindings);
    borrowed.bindObservedPageState(77, 0);
    presonus::mainlcd_port::State state;
    Presonus::MainLCDComponent *observer = nullptr;
    deletes = cleaned = 0;
    if (argc > 1) {
      auto *provider = new Core::Portable::Component("provider");
      for (int i = 0; i < count; ++i)
        provider->addChild(new Child);
      Core::Vector<Presonus::PageComponent *> pages;
      Core::Vector<Core::Portable::View *> views;
      for (int i = 0; i < n; ++i) {
        pages.add(&borrowed);
        views.add(nullptr);
      }
      delete provider;
      pages.removeAll();
      views.removeAll();
      std::cout << cleaned << " " << pages.getCapacity() << " "
                << views.getCapacity() << " " << borrowed.getPageTag() << "\n";
    } else {
      auto *screen = new Presonus::Surface::MainScreenComponent(
          presonus::surface::MainScreenInit{}, app, state);
      tracked = screen;
      observer = screen;
      state.viewObserverSlot = &observer;
      // Opaque borrowed view identity; destructor never dereferences this
      // token.
      state.lcd =
          linked ? reinterpret_cast<Presonus::LcdView *>(&observer) : nullptr;
      state.current = &borrowed;
      for (int i = 0; i < count; ++i)
        screen->addChild(new Child);
      for (int i = 0; i < n; ++i) {
        state.pages.add(&borrowed);
        state.views.add(nullptr);
      }
      screen->~MainScreenComponent();
      int observedDeletes = deletes;
      ::operator delete(screen);
      std::cout << cleaned << " " << observedDeletes << " "
                << (observer == nullptr) << " " << (state.current == nullptr)
                << " " << state.pages.getCapacity() << " "
                << state.views.getCapacity() << " " << borrowed.getPageTag()
                << "\n";
      tracked = nullptr;
    }
  }
}
