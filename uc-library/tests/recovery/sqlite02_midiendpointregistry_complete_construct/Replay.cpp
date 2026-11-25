#include "presonus/uc/midi_endpoint_registry.hpp"

#include <array>
#include <cstddef>
#include <iostream>
#include <new>
#include <string_view>
#include <type_traits>

using namespace Presonus::UC;

extern "C" void *__real__Znam(std::size_t size);
extern "C" void __real__ZdaPv(void *address) noexcept;

namespace {
struct AllocationTrace {
  std::array<void *, 4> blocks{};
  unsigned allocated = 0;
  unsigned released = 0;
  bool valid = true;
};

AllocationTrace *trace = nullptr;

struct DerivedRegistry : MidiEndpointRegistry {};

template <typename Pointer> Pointer identity(int value) {
  static std::array<std::max_align_t, 8> objects{};
  return reinterpret_cast<Pointer>(&objects.at(value));
}

template <typename Registry> bool construct() {
  int start, delta;
  std::cin >> start >> delta;
  Registry registry;
  bool ok = !registry.hasListeners();
  auto inspect = [&ok](const auto &roster) {
    int count, capacity, growth;
    std::cin >> count >> capacity >> growth;
    ok &= roster.count() == count && roster.getCapacity() == capacity &&
          roster.getDelta() == growth;
  };
  inspect(registry.portableLocalEndpoints());
  inspect(registry.portableRemoteEndpoints());
  inspect(registry.portableListeners());
  auto &ids = registry.portableSenderIds();
  for (int index = 0; index <= delta; ++index)
    ok &= ids.newID() == start + index;
  ids.releaseID(start);
  return ok && ids.newID() == start;
}

template <typename Registry> bool destroy() {
  int expectedReleases;
  std::cin >> expectedReleases;
  AllocationTrace observer;
  trace = &observer;
  bool added;
  {
    Registry registry;
    added =
        registry.portableLocalEndpoints().add(identity<MidiEndpoint *>(1)) &&
        registry.portableRemoteEndpoints().add(identity<MidiEndpoint *>(2)) &&
        registry.portableListeners().add(identity<IMidiNetworkListener *>(3));
  }
  trace = nullptr;
  return added && observer.valid &&
         observer.allocated == static_cast<unsigned>(expectedReleases) &&
         observer.released == observer.allocated;
}

bool hasListeners() {
  int length, expected;
  std::cin >> length >> expected;
  MidiEndpointRegistry registry;
  auto &listeners = registry.portableListeners();
  for (int index = 0; index < length; ++index)
    if (!listeners.add(identity<IMidiNetworkListener *>(index)))
      return false;
  return registry.hasListeners() == static_cast<bool>(expected) &&
         listeners.count() == length;
}

bool removeListener() {
  int length;
  std::cin >> length;
  MidiEndpointRegistry registry;
  auto &listeners = registry.portableListeners();
  for (int index = 0; index < length; ++index) {
    int value;
    std::cin >> value;
    if (!listeners.add(identity<IMidiNetworkListener *>(value)))
      return false;
  }
  int removed, expectedLength;
  std::cin >> removed >> expectedLength;
  const int originalCapacity = listeners.getCapacity();
  registry.removeListener(identity<IMidiNetworkListener *>(removed));
  if (listeners.count() != expectedLength ||
      listeners.getCapacity() != originalCapacity)
    return false;
  for (int index = 0; index < expectedLength; ++index) {
    int expected;
    std::cin >> expected;
    if (listeners[index] != identity<IMidiNetworkListener *>(expected))
      return false;
  }
  return true;
}
} // namespace

extern "C" void *__wrap__Znam(std::size_t size) {
  auto *block = __real__Znam(size);
  if (trace) {
    if (trace->allocated < trace->blocks.size())
      trace->blocks[trace->allocated++] = block;
    else
      trace->valid = false;
  }
  return block;
}

extern "C" void __wrap__ZdaPv(void *address) noexcept {
  if (trace) {
    if (trace->released < trace->allocated &&
        address == trace->blocks[trace->allocated - trace->released - 1])
      ++trace->released;
    else
      trace->valid = false;
  }
  __real__ZdaPv(address);
}

int main(int argc, char **argv) {
  static_assert(!std::has_virtual_destructor_v<MidiEndpointRegistry>);
  if (argc != 2)
    return 2;
  const std::string_view task(argv[1]);
  unsigned count;
  if (!(std::cin >> count) || !count)
    return 2;
  for (unsigned index = 0; index < count; ++index) {
    bool ok;
    if (task == "complete_construct")
      ok = construct<MidiEndpointRegistry>();
    else if (task == "base_construct")
      ok = construct<DerivedRegistry>();
    else if (task == "complete_destroy")
      ok = destroy<MidiEndpointRegistry>();
    else if (task == "base_destroy")
      ok = destroy<DerivedRegistry>();
    else if (task == "has_listeners")
      ok = hasListeners();
    else if (task == "remove_listener")
      ok = removeListener();
    else
      return 2;
    if (!ok || !std::cin) {
      std::cerr << "Replay mismatch at case " << index << '\n';
      return 1;
    }
  }
  std::cout << count << " " << task << " portable cases\n";
}
