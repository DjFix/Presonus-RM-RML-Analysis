#include "core/portable/gui/coreview.h"
#include "presonus/MainLCDComponent.hpp"
#include "presonus/PageComponent.hpp"

#include <cstdlib>
#include <iostream>
#include <string_view>

namespace {
class IdleApplication final : public presonus::mainlcd_port::Application {
public:
  Presonus::PageComponent *findPage(int) const override { std::abort(); }
  void requestPage(Presonus::PageComponent *) override { std::abort(); }
  void showNextPage() override { std::abort(); }
  int startPageTag() const override { std::abort(); }
  Core::Portable::RootView *rootView(Presonus::LcdView *) const override {
    std::abort();
  }
  void observeView(Presonus::LcdView *, Presonus::MainLCDComponent &) override {
    std::abort();
  }
};

using Core::Portable::WheelEvent;
using Presonus::PageComponent;

[[gnu::noinline, gnu::noipa]] void dispatch(PageComponent &page,
                                            const WheelEvent &event) {
  page.onWheelInput(event);
}

bool replay(int delta, bool indirect) {
  IdleApplication application;
  presonus::mainlcd_port::State state;
  Presonus::MainLCDComponent owner(application, state);
  PageComponent page("Wheel", "WheelForm", 96);
  page.bindObservedPageState(96, 47);
  owner.addChild(&page);
  state.current = &page;
  const WheelEvent event(delta, delta < 0 ? WheelEvent::kHorizontal
                                          : WheelEvent::kVertical);
  if (indirect)
    dispatch(page, event);
  else
    page.PageComponent::onWheelInput(event);
  const bool unchanged =
      page.isVisible() && page.getMainScreen() == &owner &&
      page.getParent() == &owner && owner.countChildren() == 1 &&
      std::string_view(page.getName()) == "Wheel" &&
      std::string_view(page.getFormName()) == "WheelForm" &&
      page.getPageTag() == 96 && page.observedByte89() == 47 &&
      event.delta == delta &&
      event.axis ==
          (delta < 0 ? WheelEvent::kHorizontal : WheelEvent::kVertical);
  state.current = nullptr;
  owner.removeChild(&page);
  return unchanged;
}

} // namespace

int main() {
  for (int delta : {-7, 19}) {
    if (!replay(delta, false))
      return 1;
    std::cout << delta << " member unchanged\n";
    if (!replay(delta, true))
      return 1;
    std::cout << delta << " virtual unchanged\n";
  }
}
