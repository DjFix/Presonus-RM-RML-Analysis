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
