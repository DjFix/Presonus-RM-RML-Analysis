#pragma once
#include "core/portable/corestorage.h"
namespace presonus::mixer {
// Independent helper retains virtual dispatch and every argument.
inline bool forwardStorageSave(const Core::Portable::IStorageFilter &filter,
                               int typeId, const char *name, void *object) {
  return filter.shouldLoad(typeId, name, object);
}
} // namespace presonus::mixer
