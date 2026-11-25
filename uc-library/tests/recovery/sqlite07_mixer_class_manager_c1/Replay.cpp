#include "presonus/MixerClassManager.hpp"

#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <new>
#include <string_view>

using Presonus::MixerClassManager;

extern "C" void
baseConstructor(MixerClassManager *) asm("_ZN8Presonus17MixerClassManagerC2Ev");
extern "C" void
baseDestructor(MixerClassManager *) asm("_ZN8Presonus17MixerClassManagerD2Ev");

namespace {
constexpr unsigned maxRecords = 6;
std::array<std::uintptr_t, maxRecords> recordAddresses{};
std::array<unsigned, maxRecords + 1> events{};
std::uintptr_t arrayAddress = 0;
unsigned recordCount = 0;
unsigned eventCount = 0;
bool observing = false;

void recordFree(void *pointer) {
  if (!observing)
    return;
  const auto address = reinterpret_cast<std::uintptr_t>(pointer);
  for (unsigned index = 0; index < recordCount; ++index) {
    if (address == recordAddresses[index]) {
      assert(eventCount < events.size());
      events[eventCount++] = index;
      return;
    }
  }
}

void arrayFree(void *pointer) {
  if (!observing)
    return;
  assert(reinterpret_cast<std::uintptr_t>(pointer) == arrayAddress);
  assert(eventCount < events.size());
  events[eventCount++] = maxRecords;
}
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __real__ZdaPv(void *);
extern "C" void __wrap__ZdlPv(void *pointer) {
  recordFree(pointer);
  __real__ZdlPv(pointer);
}
extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  recordFree(pointer);
  __real__ZdlPvm(pointer, size);
}
extern "C" void __wrap__ZdaPv(void *pointer) {
  arrayFree(pointer);
  __real__ZdaPv(pointer);
}

namespace Presonus {
struct MixerClassManagerLifetimeProbe {
  static void run(std::string_view variant, unsigned count) {
    alignas(MixerClassManager) std::byte storage[sizeof(MixerClassManager)];
    MixerClassManager *manager;
    if (variant == "c2") {
      manager = reinterpret_cast<MixerClassManager *>(storage);
      baseConstructor(manager);
      manager = std::launder(manager);
    } else {
      manager = new (storage) MixerClassManager;
    }

    auto &classes = manager->classes_;
    assert(classes.count() == 0 && classes.getCapacity() == 0);
    assert(classes.getItems() == nullptr && classes.getDelta() == 5);
    std::printf("empty 0 0 %d\n", classes.getDelta());

    std::array<std::array<char, 2>, maxRecords> names{};
    for (unsigned index = 0; index < count; ++index) {
      names[index][0] = static_cast<char>('a' + index);
      auto *record =
          new MixerClassManager::MixerClass{names[index].data(), nullptr};
      assert(classes.add(record));
      recordAddresses[index] = reinterpret_cast<std::uintptr_t>(record);
    }
    assert(classes.count() == static_cast<int>(count));
    arrayAddress = reinterpret_cast<std::uintptr_t>(classes.getItems());
    recordCount = count;
    observing = true;
    if (variant == "d2")
      baseDestructor(manager);
    else
      manager->~MixerClassManager();
    observing = false;

    assert(eventCount == count + (count ? 1 : 0));
    for (unsigned index = 0; index < count; ++index) {
      assert(events[index] == index);
      assert(names[index][0] == static_cast<char>('a' + index));
      assert(names[index][1] == '\0');
      std::printf("record_delete %u\n", index);
    }
    if (count) {
      assert(events[count] == maxRecords);
      std::puts("vector_storage_release");
    }
  }
};
} // namespace Presonus

int main(int argc, char **argv) {
  assert(argc == 3);
  const std::string_view variant = argv[1];
  assert(variant == "c1" || variant == "c2" || variant == "d1" ||
         variant == "d2");
  const auto count = std::strtoul(argv[2], nullptr, 10);
  assert(count == 0 || count == 2 || count == maxRecords);
  Presonus::MixerClassManagerLifetimeProbe::run(variant, count);
}
