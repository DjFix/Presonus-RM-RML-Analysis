#pragma once
#include "core/public/corevector.h"
namespace Presonus::Panel {
class PresetNameCache;
// Portable source port. Storage and pointer return are chosen declarations;
// original layout, ownership and ordinary return declaration remain unresolved.
class PresetNameManager {
public:
  PresetNameManager(PresetNameCache *const *items, int count)
      : caches(items, count) {}
  PresetNameCache *getCache(int index) const;

private:
  Core::ConstVector<PresetNameCache *> caches;
};
} // namespace Presonus::Panel
