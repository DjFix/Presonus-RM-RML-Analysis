#include "presonus/MainLCDComponent.hpp"
#include "presonus/PageComponent.hpp"
#include <iostream>
#include <stdexcept>
struct Bindings : presonus::page::Bindings {
  void *castOwner(void *, int) const override { return nullptr; }
  const void *currentPage(void *) const override { return nullptr; }
  void stopTextInput(void *, bool) const override {}
  bool isEditingText(void *) const override { return false; }
};
struct App : presonus::mainlcd_port::Application {
  Presonus::PageComponent *findPage(int) const override { return nullptr; }
  void requestPage(Presonus::PageComponent *) override {}
  void showNextPage() override {}
  int startPageTag() const override { return 0; }
  Core::Portable::RootView *rootView(Presonus::LcdView *) const override {
    return nullptr;
  }
  void observeView(Presonus::LcdView *, Presonus::MainLCDComponent &) override {
  }
};
int main() {
  Bindings bindings;
  App app;
  int c, n, a, t, f, b, k, expectedPush;
  while (std::cin >> c >> n >> a >> t >> f >> b >> k >> expectedPush) {
    Presonus::PageComponent current(nullptr, bindings), next(nullptr, bindings),
        marker(nullptr, bindings);
    current.bindObservedPageState(t, static_cast<unsigned char>(f));
    next.bindObservedPageState(123, static_cast<unsigned char>(f));
    presonus::mainlcd_port::State state;
    state.current = c ? &current : nullptr;
    state.next = n ? (a ? &current : &next) : nullptr;
    state.back = b ? &marker : nullptr;
    Presonus::MainLCDComponent lcd(app, state);
    for (int i = 0; i < k; ++i)
      lcd.pushBackPage(&marker);
    // A separate actual pinned CCL vector captures expected container
    // evolution.
    Core::FixedSizeVector<Presonus::PageComponent *, 10> provider;
    for (int i = 0; i < k; ++i)
      provider.add(&marker);
    int tag = lcd.getCurrentPageTag();
    lcd.setupBackPage();
    bool pushed = state.backPages.count() != k ||
                  (k == 9 && state.backPages.last() == &current);
    if (expectedPush) {
      if (provider.count() == 9)
        provider.removeFirst();
      provider.add(&current);
    }
    if (provider.count() != state.backPages.count())
      return 2;
    for (int i = 0; i < provider.count(); ++i)
      if (provider[i] != state.backPages[i])
        return 3;
    std::cout << tag << ' ' << (state.back != nullptr) << ' ' << pushed << '\n';
  }
  // Default owned State and unbound application guard remain live.
  Presonus::MainLCDComponent owned;
  if (owned.getCurrentPageTag() != -1 || owned.hasBackPage())
    return 4;
  owned.setupBackPage();
  try {
    owned.showStartPage();
    return 5;
  } catch (const std::logic_error &) {
  }
}
