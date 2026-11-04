#include "presonus/panel/PresetNameManager.hpp"
#include "presonus/panel/PresetNameCache.hpp"
namespace Presonus::Panel {
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
