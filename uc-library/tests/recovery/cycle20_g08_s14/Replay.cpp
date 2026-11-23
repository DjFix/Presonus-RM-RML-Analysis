#include "core/portable/gui/corecontrols.h"
#include "presonus/MainLCDComponent.hpp"
#include "presonus/PageComponent.hpp"
#include "presonus/surface/MainScreenComponent.hpp"

#include <iostream>
#include <stdexcept>
#include <tuple>
#include <type_traits>

using Core::Portable::Control;
using Presonus::MainLCDComponent;
using Presonus::PageComponent;
using presonus::mainlcd_port::State;
using Presonus::Surface::MainScreenComponent;

namespace {
struct PageBindings final : presonus::page::Bindings {
  void *castOwner(void *, int) const override { return nullptr; }
  const void *currentPage(void *) const override { return nullptr; }
  void stopTextInput(void *, bool) const override {}
  bool isEditingText(void *) const override { return false; }
};
class App final : public presonus::mainlcd_port::Application {
public:
  explicit App(PageComponent &start) : start_(start) {}
  PageComponent *findPage(int tag) const override {
    ++finds;
    return tag == 0 ? &start_ : nullptr;
  }
  void requestPage(PageComponent *page) override { requests = page; }
  void showNextPage() override { ++nexts; }
  int startPageTag() const override { return 0; }
  Core::Portable::RootView *rootView(Presonus::LcdView *) const override {
    ++roots;
    return nullptr;
  }
  void observeView(Presonus::LcdView *, MainLCDComponent &) override {
    ++observed;
  }
  auto snapshot() const {
    return std::make_tuple(finds, requests, nexts, roots, observed);
  }

private:
  PageComponent &start_;
  mutable unsigned finds = 0;
  PageComponent *requests = nullptr;
  unsigned nexts = 0;
  mutable unsigned roots = 0;
  unsigned observed = 0;
};

auto observe(MainLCDComponent &lcd, const State &state, const App &app,
             const PageComponent &page, const PageComponent &previous,
             const Control &control) {
  return std::make_tuple(
      state.lcd, state.viewObserverSlot, state.current, state.next, state.back,
      state.pages.count(), state.views.count(), state.backPages.count(),
      state.stackConfigured, lcd.getCurrentPage(), lcd.getCurrentPageTag(),
      lcd.countParameters(), page.getPageTag(), previous.getPageTag(),
      control.getSize(), app.snapshot());
}

void dispatch(MainLCDComponent &lcd, PageComponent &page,
              PageComponent *previous, Control *control) {
  (void)page;
  (void)previous;
  (void)control;
  lcd.onSelectedChannelChanged();
}

void qualified(MainLCDComponent &lcd, PageComponent &page,
               PageComponent *previous, Control *control) {
  (void)page;
  (void)previous;
  (void)control;
  lcd.MainLCDComponent::onSelectedChannelChanged();
}
} // namespace

int main() {
  static_assert(
      std::is_same_v<decltype(&MainLCDComponent::onSelectedChannelChanged),
                     void (MainLCDComponent::*)()>);
  unsigned virtualDispatch, seed, argumentPresent, previousPresent;
  while (std::cin >> virtualDispatch >> seed >> argumentPresent >>
         previousPresent) {
    PageBindings bindings;
    PageComponent page(nullptr, bindings, "page");
    PageComponent previous(nullptr, bindings, "previous");
    PageComponent start(nullptr, bindings, "start");
    page.bindObservedPageState(3, static_cast<unsigned char>(seed));
    previous.bindObservedPageState(4, 0);
    start.bindObservedPageState(0, 0);
    Control control;
    App app(start);
    State state;
    state.current = &page;
    state.next = seed % 2 ? &previous : nullptr;
    state.back = &start;
    state.pages.add(&page);
    state.pages.add(&previous);
    state.backPages.add(&start);
    state.stackConfigured = true;
    MainLCDComponent lcd(app, state);
    auto *previousArgument = previousPresent ? &previous : nullptr;
    auto *controlArgument = argumentPresent ? &control : nullptr;
    const auto before = observe(lcd, state, app, page, previous, control);
    if (virtualDispatch)
      dispatch(lcd, page, previousArgument, controlArgument);
    else
      qualified(lcd, page, previousArgument, controlArgument);
    const bool unchanged =
        before == observe(lcd, state, app, page, previous, control);

    State derivedState;
    derivedState.current = &page;
    MainScreenComponent screen(presonus::surface::MainScreenInit{}, app,
                               derivedState);
    MainLCDComponent &baseScreen = screen;
    dispatch(baseScreen, page, previousArgument, controlArgument);
    if (std::get<0>(app.snapshot()) != 1 ||
        std::get<1>(app.snapshot()) != &start)
      return 4;
    std::cout << unchanged << '\n';
  }
  return std::cin.eof() ? 0 : 3;
}
