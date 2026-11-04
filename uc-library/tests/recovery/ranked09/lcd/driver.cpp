#include "presonus/MainLCDComponent.hpp"
#include <cstdint>
#include <cstdlib>
#include <iostream>
namespace {
struct App final : presonus::mainlcd_port::Application {
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
Presonus::PageComponent *page(std::uintptr_t value) {
  return reinterpret_cast<Presonus::PageComponent *>(value);
}
} // namespace
int main(int argc, char **argv) {
  if (argc != 4)
    return 64;
  const int target = std::atoi(argv[1]), count = std::atoi(argv[2]);
  App app;
  presonus::mainlcd_port::State state;
  for (int i = 0; i < count; ++i)
    state.backPages.add(page(0x500000 + i * 0x100));
  // Seed inactive slots as the original native fixture does; this observes
  // removeLast/removeFirst clearing through the real CCL sentinel.
  for (int i = count; i < 10; ++i)
    state.backPages.getItems()[i] = page(0x500000 + i * 0x100);
  Presonus::MainLCDComponent component(app, state);
  // Unconfigured legacy mode ignores new storage until an explicit stack call.
  state.back = page(0x550000);
  if (!component.hasBackPage())
    return 69;
  state.back = nullptr;
  if (component.hasBackPage())
    return 70;
  // After configuration this legacy nonnull value must not fake stack content.
  state.back = page(0x550000);
  std::uintptr_t result = 0;
  if (target == 2)
    result = reinterpret_cast<std::uintptr_t>(component.popBackPage());
  else if (target == 3) {
    component.pushBackPage(page(std::strtoull(argv[3], nullptr, 10)));
    result = state.backPages.count();
  } else
    return 65;
  if (!state.stackConfigured ||
      component.hasBackPage() != (state.backPages.count() != 0))
    return 66;
  state.current = page(0x530000);
  state.next = nullptr;
  if (component.getCurrentPage() != state.current)
    return 67;
  state.next = page(0x540000);
  if (component.getCurrentPage() != state.next)
    return 68;
  std::cout << state.backPages.count() << ' ' << result;
  for (int i = 0; i < 10; ++i)
    std::cout << ' '
              << reinterpret_cast<std::uintptr_t>(
                     state.backPages.getItems()[i]);
  std::cout << '\n';
}
