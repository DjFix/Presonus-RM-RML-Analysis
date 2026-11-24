#include "presonus/panel/PresetNameCache.hpp"
#include "presonus/panel/PresetNameManager.hpp"
#include <cstring>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

namespace {
using Presonus::Panel::PresetNameCache;
using Presonus::Panel::PresetNameManager;

struct Sink : PresetNameCache::ObserverSink {
  int events = 0;

  void changed(PresetNameCache::Delegate *, PresetNameCache &, int,
               const char *, const char *) override {
    ++events;
  }
  void rebuilt(PresetNameCache::Delegate *, PresetNameCache &) override {
    ++events;
  }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const int count = std::stoi(argv[1]);
  Sink sink;
  std::vector<std::unique_ptr<PresetNameCache>> entries;
  PresetNameManager manager;
  for (int index = 0; index < count; ++index) {
    const auto type = "preset" + std::to_string(index);
    auto cache = std::make_unique<PresetNameCache>(
        type.c_str(),
        Core::Portable::FileName("/proc/self/presonus-recovery-fixture"), 1, 0,
        sink);
    cache->rebuild();
    cache->addObserver(
        reinterpret_cast<PresetNameCache::Delegate *>(cache.get()));
    cache->cachePreset(type.c_str(), "test", 0);
    if (!manager.sourcePortAddCache(cache.get()))
      return 3;
    entries.push_back(std::move(cache));
  }
  const int beforeEvents = sink.events;
  const int beforeCapacity = manager.sourcePortCacheCapacity();
  const int result = manager.countCaches();
  const auto &receiver = manager;
  if (receiver.countCaches() != result ||
      receiver.sourcePortCacheCount() != result ||
      receiver.sourcePortCacheCapacity() != beforeCapacity ||
      sink.events != beforeEvents)
    return 4;
  for (int index = 0; index < count; ++index) {
    const auto type = "preset" + std::to_string(index);
    auto *const entry = receiver.getCache(index);
    Core::CString64 name;
    Core::CString32 category;
    if (entry != entries[index].get() ||
        receiver.lookupCache(type.c_str()) != entry ||
        !entry->getPresetInfo(name, category, 0) ||
        std::strcmp(name.str(), type.c_str()) != 0 ||
        std::strcmp(category.str(), "test") != 0)
      return 5;
  }
  std::cout << result << ' ' << beforeCapacity << '\n';
}
