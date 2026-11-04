#include "core/portable/gui/corecontrols.h"
#include "presonus/MainLCDComponent.hpp"
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>
namespace {
constexpr std::uintptr_t This = 0x200000;
std::vector<std::string> trace;
bool editing = false;
void event(const char *name, std::uintptr_t a = 0) {
  trace.push_back(std::string(name) + ":" + std::to_string(a));
}
struct App final : presonus::mainlcd_port::Application {
  Presonus::PageComponent *lookup = nullptr;
  int tag = 0;
  std::uintptr_t observer = 0;
  Presonus::PageComponent *findPage(int value) const override {
    event("getPageByTag", static_cast<std::uint32_t>(value));
    return lookup;
  }
  void requestPage(Presonus::PageComponent *value) override {
    event("showPagePointer", reinterpret_cast<std::uintptr_t>(value));
  }
  void showNextPage() override { event("showNextPage"); }
  int startPageTag() const override {
    event("startTag");
    return tag;
  }
  Core::Portable::RootView *rootView(Presonus::LcdView *value) const override {
    return reinterpret_cast<Core::Portable::RootView *>(value);
  }
  void observeView(Presonus::LcdView *, Presonus::MainLCDComponent &) override {
    observer = This + 0x84;
  }
};
} // namespace
extern "C" bool wrappedEditing(Core::Portable::RootView *) asm(
    "__wrap__ZN4Core8Portable9TextInput9isEditingEPNS0_8RootViewE");
extern "C" bool wrappedEditing(Core::Portable::RootView *root) {
  event("isEditing", reinterpret_cast<std::uintptr_t>(root));
  return editing;
}
extern "C" void wrappedStop(Core::Portable::RootView *, bool) asm(
    "__wrap__ZN4Core8Portable9TextInput4stopEPNS0_8RootViewEb");
extern "C" void wrappedStop(Core::Portable::RootView *, bool canceled) {
  event("stopTextInput", canceled);
}
extern "C" void realIdle(Core::Portable::Component *) asm(
    "__real__ZN4Core8Portable9Component6onIdleEv");
extern "C" void wrappedIdle(Core::Portable::Component *) asm(
    "__wrap__ZN4Core8Portable9Component6onIdleEv");
extern "C" void wrappedIdle(Core::Portable::Component *component) {
  event("componentIdle");
  realIdle(component);
}
extern "C" bool realEditing(Core::Portable::RootView *) asm(
    "__real__ZN4Core8Portable9TextInput9isEditingEPNS0_8RootViewE");
extern "C" void
realStop(Core::Portable::RootView *,
         bool) asm("__real__ZN4Core8Portable9TextInput4stopEPNS0_8RootViewEb");
int main(int argc, char **argv) {
  if (argc == 2 && std::string(argv[1]) == "--provider-smoke") {
    Core::Portable::RootView root;
    if (realEditing(&root))
      return 2;
    realStop(&root, false);
    realStop(&root, true);
    std::cout << "actual CCL TextInput empty-modal smoke passed\n";
    return 0;
  }
  if (argc != 10)
    return 64;
  auto number = [&](int i) { return std::strtoull(argv[i], nullptr, 10); };
  const int target = number(1);
  presonus::mainlcd_port::State state;
  state.lcd = reinterpret_cast<Presonus::LcdView *>(number(2));
  state.current = reinterpret_cast<Presonus::PageComponent *>(number(3));
  state.next = reinterpret_cast<Presonus::PageComponent *>(number(4));
  state.back = reinterpret_cast<Presonus::PageComponent *>(number(5));
  auto arg = number(6);
  editing = number(7);
  App app;
  app.lookup = reinterpret_cast<Presonus::PageComponent *>(number(8));
  app.tag = static_cast<int>(number(9));
  Presonus::MainLCDComponent component(app, state);
  std::uintptr_t result = 0;
  switch (target) {
  case 1:
    result = component.hasBackPage();
    break;
  case 2:
    result = reinterpret_cast<std::uintptr_t>(component.getCurrentPage());
    break;
  case 3:
    result = component.isEditingText();
    break;
  case 4:
    // Opaque identity boundary only: neither implementation reads the referent.
    component.onDestroyed(*reinterpret_cast<const Presonus::LcdView *>(arg));
    break;
  case 5:
    component.setLcdView(reinterpret_cast<Presonus::LcdView *>(arg));
    break;
  case 6:
    component.stopTextInput(arg);
    break;
  case 7:
    component.onIdle();
    break;
  case 8:
    component.showPage(static_cast<int>(arg));
    break;
  case 9:
    result = component.castTo(static_cast<int>(arg)) ? This : 0;
    break;
  case 10:
    component.showStartPage();
    break;
  default:
    return 65;
  }
  std::cout << result << ' ' << reinterpret_cast<std::uintptr_t>(state.lcd)
            << ' ' << app.observer;
  for (const auto &entry : trace)
    std::cout << ' ' << entry;
  std::cout << '\n';
}
