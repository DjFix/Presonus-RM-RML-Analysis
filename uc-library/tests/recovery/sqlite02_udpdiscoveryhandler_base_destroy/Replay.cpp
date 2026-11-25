#include "presonus/uc/udp_discovery.hpp"

#include <cassert>
#include <cstddef>
#include <cstdlib>
#include <iostream>
#include <string_view>

namespace {
void *vectorArray{};
bool arrayFreed{};

class Fixture final : public Presonus::UC::UDPDiscoveryHandler {
public:
  using UDPDiscoveryHandler::discoveryState;
  using UDPDiscoveryHandler::UDPDiscoveryHandler;

private:
  bool registerServer(void *&, const Presonus::UC::DiscoveryDescriptor &,
                      int) override {
    std::abort();
  }
  void processDiscovery() override { std::abort(); }
  void onMulticastEvent(const char *, unsigned short, unsigned short, int,
                        Presonus::UC::EventItem *) override {
    std::abort();
  }
};
} // namespace

extern "C" void __real__ZdaPv(void *);
extern "C" void __real__ZdaPvm(void *, std::size_t);
extern "C" void __wrap__ZdaPv(void *ptr) {
  if (vectorArray && vectorArray == ptr)
    arrayFreed = true;
  __real__ZdaPv(ptr);
}
extern "C" void __wrap__ZdaPvm(void *ptr, std::size_t size) {
  if (vectorArray && vectorArray == ptr)
    arrayFreed = true;
  __real__ZdaPvm(ptr, size);
}

int main(int argc, char **argv) {
  assert(argc == 2);
  const std::string_view variant = argv[1];
  const bool constructor = variant == "C1" || variant == "C2";
  assert(constructor || variant == "D1" || variant == "D2");
  using namespace presonus::uc;
  DiscoveryEntryState entryState;
  entryState.identifier = 280;
  Presonus::UC::UDPDiscoveryEntry entry(DiscoverySourcePortTag{}, entryState);
  for (int i = 0; i < 4; ++i) {
    const bool allocated = !constructor && i % 2 == 1;
    arrayFreed = false;
    {
      Fixture object;
      auto &state = object.discoveryState();
      assert(state.entries.getDelta() == 5);
      assert(state.entries.getCapacity() == 0 && state.entries.isEmpty());
      assert(!state.entries.getItems());
      assert(!state.connection && !state.reply && !state.ownership);
      assert(!state.browsing && !state.counter28 && !state.counter2c);
      if (allocated) {
        const bool added = state.entries.add(&entry);
        assert(added);
        vectorArray = state.entries.getItems();
        assert(vectorArray && !arrayFreed);
      }
    }
    assert(arrayFreed == allocated && entryState.identifier == 280);
    vectorArray = nullptr;
    std::cout << (constructor ? "resize 0\n"
                  : allocated ? "destroy release\n"
                              : "destroy\n");
  }
  DiscoveryHandlerState borrowed;
  const bool added = borrowed.entries.add(&entry);
  assert(added);
  borrowed.counter28 = 44;
  auto *entries = borrowed.entries.getItems();
  {
    Fixture object(DiscoverySourcePortTag{}, borrowed);
    assert(&object.discoveryState() == &borrowed);
    Fixture copy(object);
    assert(&copy.discoveryState() == &borrowed);
    assert(object.startBrowsing() && borrowed.browsing == 1);
    object.stopBrowsing();
    assert(borrowed.browsing == 0);
  }
  assert(borrowed.counter28 == 44 && borrowed.entries.count() == 1);
  assert(borrowed.entries.getItems() == entries &&
         borrowed.entries.at(0) == &entry);
}
