#include "presonus/panel/PresetNameManager.hpp"
#include "presonus/panel/PresetNameCache.hpp"
#include <cstring>
DEFINE_SINGLETON(Presonus::Panel::PresetNameManager)
namespace Presonus::Panel {
PresetNameManager::PresetNameManager() : caches(10, 5) {}
PresetNameManager::PresetNameManager(PresetNameCache *const *items, int count)
    : caches(10, 5) {
  for (int i = 0; i < count; ++i)
    caches.add(items[i]);
}

PresetNameCache *PresetNameManager::lookupCache(const char *name) const {
  for (int i = 0; i < caches.count(); ++i)
    if (std::strcmp(caches[i]->type.str(), name ? name : "") == 0)
      return caches[i];
  return nullptr;
}
PresetNameCache *PresetNameManager::getCache(int index) const {
  return caches.at(index);
}
void PresetNameManager::rebuildAllCaches() const {
  auto *const *items = caches.getItems();
  const int count = caches.count();
  for (int i = 0; i < count; ++i) {
    items[i]->dirty = true;
    items[i]->rebuild();
  }
}
} // namespace Presonus::Panel

namespace Presonus::Panel {
void PresetNameManager::cachePreset(const char *type, const char *name,
                                    const char *category, int slot) {
  if (auto *cache = lookupCache(type))
    cache->cachePreset(name, category, slot);
}
bool PresetNameManager::getPresetInfo(Core::CStringBuffer<64> &name,
                                      Core::CStringBuffer<32> &category,
                                      int slot, const char *type) {
  if (auto *cache = lookupCache(type))
    return cache->getPresetInfo(name, category, slot);
  return false;
}
Core::Portable::FileName
PresetNameManager::getPresetFilePath(int slot, const char *type, bool full) {
  if (auto *cache = lookupCache(type))
    return cache->getFileNameForSlot(static_cast<unsigned>(slot), full);
  return Core::Portable::FileName("");
}
PresetNameCache *PresetNameManager::lookupCacheForRemoteUrl(const char *url) {
  Core::Portable::FileName remote(url);
  for (int i = 0; i < caches.count(); ++i) {
    Core::Portable::FileName prefix("presets/");
    prefix += caches[i]->type;
    if (std::strstr(remote.str(), prefix.str()) == remote.str())
      return caches[i];
  }
  return nullptr;
}
} // namespace Presonus::Panel
