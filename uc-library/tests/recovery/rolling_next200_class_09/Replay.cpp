#include "presonus/mixer/NetworkSetupComponent.hpp"
#include "presonus/uc/NetworkItem.hpp"
#include <iostream>
#include <stdexcept>
#include <string_view>

namespace {
struct UnusedServices final : presonus::mixer::NetworkSetupServices {
  [[noreturn]] static void unexpected() {
    throw std::logic_error("unexpected network service call");
  }
  using Item = Presonus::UC::NetworkItem;
  using Root = Presonus::UC::ClientRootComponent;
  int itemKind(const Item &) const override { unexpected(); }
  int itemFilter(const Item &) const override { unexpected(); }
  const char *itemName(const Item &) const override { unexpected(); }
  const char *itemSerial(const Item &) const override { unexpected(); }
  void itemTitle(const Item &, Core::CStringBuffer<128> &) const override {
    unexpected();
  }
  Root *component(const Item &) const override { unexpected(); }
  Presonus::UC::ClientImplementation &eventSender(Root &) const override {
    unexpected();
  }
  void acquire(Item &) override { unexpected(); }
  void release(Item &, bool) override { unexpected(); }
  void *mixerForClient(Root &) override { unexpected(); }
  void setRemoteMixer(void *) override { unexpected(); }
  void remoteIdle() override { unexpected(); }
  void restoredSelection() override { unexpected(); }
  void serverParamChanged(Core::Portable::Parameter *, int) override {
    unexpected();
  }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const std::string_view mode(argv[1]);
  if (mode != "item" && mode != "null")
    return 2;
  const bool hasItem = mode == "item";
  Core::Portable::Component parameters;
  UnusedServices services;
  std::uint64_t ticks = 42;
  Presonus::UC::NetworkItem item(&ticks);
  item.setPortableIdentity("callback sentinel");
  presonus::mixer::NetworkSetupState state{parameters, services, {}};
  if (hasItem)
    state.items.add(&item);
  state.selected = hasItem ? &item : nullptr;
  state.hasRemoteHandler = hasItem;
  state.restoreTicks = &ticks;
  state.mixerHandler = &ticks;
  Presonus::Mixer::NetworkSetupComponent component(state);

  component.onServerChanged(hasItem ? &item : nullptr);

  const bool receiverUnchanged =
      state.selected == (hasItem ? &item : nullptr) &&
      state.hasRemoteHandler == hasItem && state.restoreTicks == &ticks &&
      ticks == 42 && state.mixerHandler == &ticks &&
      state.persistentSelection == nullptr && state.milliseconds == nullptr &&
      state.items.count() == (hasItem ? 1 : 0) &&
      (!hasItem || state.items[0] == &item);
  const bool itemUnchanged =
      item.getComponent() == &ticks &&
      std::string_view(static_cast<const char *>(item.portableIdentity())) ==
          "callback sentinel";
  std::cout << std::boolalpha << "{\"receiver_unchanged\":" << receiverUnchanged
            << ",\"item_unchanged\":" << itemUnchanged << "}\n";
}
