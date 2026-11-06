#pragma once
#include "core/portable/corestorage.h"
// Portable source contract: bool and CCL inheritance are intentional
// adaptations. Original return declaration, layout and ARM ABI remain
// unresolved.
class AltMemoryFilter : public Core::Portable::IStorageFilter {
public:
  void *castTo(TypeID id) override {
    return id == Core::Portable::IStorageFilter::kTypeID
               ? static_cast<Core::Portable::IStorageFilter *>(this)
               : nullptr;
  }
  bool shouldLoad(int typeId, const char *name, void *object) const override;
  bool shouldSave(int typeId, const char *name, void *object) const override;
};
