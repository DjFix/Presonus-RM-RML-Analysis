#pragma once
#include "core/portable/coresingleton.h"
#include "core/public/corevector.h"
namespace Presonus::Panel {
class PresetNameCache;
// Portable source port. Storage and pointer return are chosen declarations;
// original layout, ownership and ordinary return declaration remain unresolved.
class PresetNameManager : public Core::Portable::Singleton<PresetNameManager> {
public:
  PresetNameManager();
  PresetNameManager(PresetNameCache *const *items, int count);
  // Borrowed entries; this is the only authoritative cache collection.
  bool sourcePortAddCache(PresetNameCache *cache) { return caches.add(cache); }
  int sourcePortCacheCount() const { return caches.count(); }
  int sourcePortCacheCapacity() const { return caches.getCapacity(); }
  PresetNameCache *getCache(int index) const;
  void rebuildAllCaches() const;
  PresetNameCache *lookupCache(const char *) const;

private:
  Core::Vector<PresetNameCache *> caches;
};
} // namespace Presonus::Panel
