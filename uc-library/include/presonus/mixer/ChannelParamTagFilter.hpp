#pragma once
#include "core/portable/corestorage.h"
namespace Presonus::Mixer {
// Portable source contract: bool and CCL inheritance are intentional
// adaptations. Original return declaration, layout and ARM ABI remain
// unresolved.
class ChannelParamTagFilter : public Core::Portable::IStorageFilter {
public:
  void *castTo(TypeID id) override {
    return id == Core::Portable::IStorageFilter::kTypeID
               ? static_cast<Core::Portable::IStorageFilter *>(this)
               : nullptr;
  }
  ChannelParamTagFilter(int tag, int channelIndex = -1)
      : tag_(tag), channelIndex_(channelIndex) {}
  bool shouldLoad(int typeId, const char *name, void *object) const override;
  bool shouldSave(int typeId, const char *name, void *object) const override;

private:
  int tag_;
  int channelIndex_;
};
} // namespace Presonus::Mixer
