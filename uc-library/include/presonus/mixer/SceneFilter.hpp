#pragma once
#include "core/portable/coreparams.h"
#include "core/portable/corestorage.h"
#include <array>
#include <cstdint>
namespace Presonus::Mixer {
class MixerComponentBase;
// Portable source port using real CCL providers and explicit app bindings.
// Ordinary return spelling, native layout and ARM interoperability are
// unresolved.
class SceneFilter : public Core::Portable::IStorageFilter {
public:
  explicit SceneFilter(MixerComponentBase &);
  SceneFilter(const SceneFilter &);
  void *castTo(TypeID id) override {
    return id == IStorageFilter::kTypeID ? static_cast<IStorageFilter *>(this)
                                         : nullptr;
  }
  void refresh();
  bool shouldLoad(int, const char *, void *) const override;
  bool shouldSave(int, const char *, void *) const override;
  // Independent source-port controls/observations, not recovered interfaces.
  void setSceneRecallEnabled(bool enabled) { enabled_ = enabled; }
  bool sceneRecallEnabled() const { return enabled_; }
  std::uint32_t mask() const { return mask_; }
  Core::Portable::Parameter *cachedParameter(unsigned i) const {
    return cached_.at(i);
  }

private:
  MixerComponentBase &mixer_;
  bool enabled_ = true;
  std::uint32_t mask_ = 0;
  std::array<Core::Portable::Parameter *, 10> cached_{};
  bool bit(unsigned i) const { return (mask_ & (1u << i)) != 0; }
};
} // namespace Presonus::Mixer
