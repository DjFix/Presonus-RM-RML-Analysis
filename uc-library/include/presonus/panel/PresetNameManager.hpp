#pragma once
#include "core/portable/corefilename.h"
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
  // The original ordinary return type is unresolved.
  int countCaches() const;
  int sourcePortCacheCount() const { return countCaches(); }
  int sourcePortCacheCapacity() const { return caches.getCapacity(); }
  PresetNameCache *getCache(int index) const;
  void rebuildAllCaches() const;
  PresetNameCache *lookupCache(const char *) const;
  // Source-port ordinary returns remain provisional; no ARM layout claim.
  void cachePreset(const char *type, const char *name, const char *category,
                   int slot);
  bool getPresetInfo(Core::CStringBuffer<64> &, Core::CStringBuffer<32> &, int,
                     const char *);
  Core::Portable::FileName getPresetFilePath(int, const char *, bool);
  PresetNameCache *lookupCacheForRemoteUrl(const char *);

private:
  Core::Vector<PresetNameCache *> caches;
};
} // namespace Presonus::Panel
