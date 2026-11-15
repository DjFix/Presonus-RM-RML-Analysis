#include "core/portable/gui/coreview.h"
#include "presonus/MainLCDComponent.hpp"
#include <iostream>
#include <stdexcept>
#include <string>
namespace presonus::mainlcd_port {
struct ConstructionAccess {
  static State &state(Presonus::MainLCDComponent &v) { return v.state; }
  static bool owned(Presonus::MainLCDComponent &v) {
    return &v.state == &v.ownedState;
  }
  static bool unbound(Presonus::MainLCDComponent &v) {
    return v.application == nullptr;
  }
  static auto word8c(Presonus::MainLCDComponent &v) { return v.observedWord8c; }
  static auto wordF4(Presonus::MainLCDComponent &v) { return v.observedWordF4; }
};
} // namespace presonus::mainlcd_port
namespace {
// Test-only observable application boundary; never installed in production.
struct ApplicationProbe final : presonus::mainlcd_port::Application {
  mutable int seenTag = -1;
  int nextCalls = 0, requests = 0;
  Presonus::PageComponent *findPage(int tag) const override {
    seenTag = tag;
    return nullptr;
  }
  void requestPage(Presonus::PageComponent *) override { ++requests; }
  void showNextPage() override { ++nextCalls; }
  int startPageTag() const override { return 7; }
  Core::Portable::RootView *rootView(Presonus::LcdView *) const override {
    throw std::logic_error("unexpected test root lookup");
  }
  void observeView(Presonus::LcdView *, Presonus::MainLCDComponent &) override {
    throw std::logic_error("unexpected test observation");
  }
};
} // namespace
int main(int argc, char **argv) {
  if (argc == 2 && std::string(argv[1]) == "--observe-provider") {
    Core::Portable::Component component("");
    Core::Vector<Core::Portable::View *> views;
    Core::Vector<Presonus::PageComponent *> pages;
    Core::FixedSizeVector<Presonus::PageComponent *, 10> stack;
    bool vr = views.resize(0), pr = pages.resize(0);
    std::cout << "{\"empty_name\":"
              << (component.getName().isEmpty() ? "true" : "false")
              << ",\"views_count\":" << views.count()
              << ",\"views_capacity\":" << views.getCapacity()
              << ",\"views_delta\":" << views.getDelta()
              << ",\"pages_count\":" << pages.count()
              << ",\"pages_capacity\":" << pages.getCapacity()
              << ",\"pages_delta\":" << pages.getDelta()
              << ",\"stack_count\":" << stack.count()
              << ",\"views_resize\":" << (vr ? "true" : "false")
              << ",\"pages_resize\":" << (pr ? "true" : "false") << "}\n";
    return 0;
  }
  Presonus::MainLCDComponent component;
  using A = presonus::mainlcd_port::ConstructionAccess;
  auto &s = A::state(component);
  if (!A::owned(component) || !A::unbound(component) || s.lcd || s.current ||
      s.next || s.back || !s.stackConfigured || !s.backPages.isEmpty() ||
      !s.views.isEmpty() || !s.pages.isEmpty() || s.views.getDelta() != 5 ||
      s.pages.getDelta() != 5 || A::word8c(component) != 40 ||
      A::wordF4(component) != 0 || component.hasBackPage() ||
      component.getCurrentPage() || component.isEditingText())
    return 1;
  int unsupported = 0;
  try {
    component.showPage(1);
  } catch (const std::logic_error &) {
    ++unsupported;
  }
  try {
    component.showStartPage();
  } catch (const std::logic_error &) {
    ++unsupported;
  }
  try {
    component.onIdle();
  } catch (const std::logic_error &) {
    ++unsupported;
  }
  if (unsupported != 3)
    return 2;
  // Defined stack source-port operations do not need an application binding.
  component.pushBackPage(nullptr);
  if (!component.hasBackPage())
    return 3;
  if (component.popBackPage() != nullptr || component.hasBackPage())
    return 4;
  ApplicationProbe application;
  component.bindApplication(application);
  component.showPage(19);
  if (application.seenTag != 19)
    return 5;
  component.showStartPage();
  component.onIdle();
  if (application.seenTag != 7 || application.nextCalls != 1 ||
      application.requests != 0)
    return 6;
  std::cout
      << "owned-default empty-vectors words40,0 checked-unbound stack passed\n";
}
