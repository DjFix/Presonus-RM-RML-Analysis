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
  ~PresetNameManager() override;
  // Source-port ownership forbids copying registrations; no original copy ABI
  // claim.
  PresetNameManager(const PresetNameManager &) = delete;
  PresetNameManager &operator=(const PresetNameManager &) = delete;
  void registerPresetType(const char *, char, const char *, int, int,
                          const char **, int);
  char getPresetTypeName(const char *) const;
  PresetNameManager(PresetNameCache *const *items, int count);
  // Explicit convenience additions are borrowed; original registrations owned.
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
  Core::Vector<PresetNameCache *> ownedCaches;
};
} // namespace Presonus::Panel
