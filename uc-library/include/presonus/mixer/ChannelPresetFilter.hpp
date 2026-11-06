#pragma once
#include "core/portable/coreparams.h"
#include "core/portable/corestorage.h"
namespace Presonus::Mixer {
// Portable source model using actual CCL interfaces. Borrowed target and
// controls must outlive this filter. No original layout, return declaration or
// ARM ABI claim.
class ChannelPresetFilter : public Core::Portable::IStorageFilter {
public:
  explicit ChannelPresetFilter(void *target = nullptr,
                               Core::Portable::Parameter *equalizer = nullptr,
                               Core::Portable::Parameter *gate = nullptr,
                               Core::Portable::Parameter *compressor = nullptr)
      : target_(target), equalizer_(equalizer), gate_(gate),
        compressor_(compressor) {}
  void *castTo(TypeID id) override {
    return id == IStorageFilter::kTypeID ? static_cast<IStorageFilter *>(this)
                                         : nullptr;
  }
  bool shouldLoad(int typeId, const char *name, void *object) const override;
  bool shouldSave(int typeId, const char *name, void *object) const override;

private:
  void *target_;
  Core::Portable::Parameter *equalizer_, *gate_, *compressor_;
};
} // namespace Presonus::Mixer
