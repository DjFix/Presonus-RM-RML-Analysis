#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/corefilename.h"

namespace Presonus::Panel {
class PresetNameCache;
}
namespace presonus::trial08 {
// Independent source-port boundary. This does not establish the original
// manager ABI. Implementations must bind the application preset manager;
// test doubles only validate this caller boundary.
struct FxRecallCache {
  Core::Vector<void *> delegates;
};
struct FxRecallServices {
  virtual ~FxRecallServices() = default;
  virtual Core::Portable::FileName presetPath(unsigned int slot,
                                              const char *category) = 0;
  virtual void presetInfo(char *name, int capacity, unsigned int slot,
                          const char *category) = 0;
  virtual FxRecallCache *lookupCache(const char *category) = 0;
};
} // namespace presonus::trial08
namespace Presonus::Panel {
// Portable source port. Field layout and inheritance are selected for actual
// CCL integration; no original ARM object layout is asserted.
class FXPresetRecallComponent : public Core::Portable::Component {
public:
  FXPresetRecallComponent(presonus::trial08::FxRecallServices &services,
                          Core::Portable::Parameter &slot,
                          Core::Portable::Parameter &loaded,
                          Core::Portable::Parameter &typeName,
                          Core::Portable::Parameter &presetName,
                          Core::Portable::Parameter &type, const char *category,
                          int effectSlot);
  void onIdle() override;
  int getSlotNum() const;
  void cacheUpdated(PresetNameCache &, int, const char *, const char *);
  bool isSlotEmpty(unsigned int) const;
  bool isChildParameter(const Core::Portable::Parameter &) const;
  void paramChanged(Core::Portable::Parameter *, int) override;
  bool getFileName(unsigned int, Core::Portable::FileName &) const;
  void getFxName(Core::Portable::Parameter &, unsigned int) const;
  void init();
  // Native preconditions: finite int-convertible values; loaded type index in
  // the selected nine-entry reverb or four-entry delay table.
  void updateFxName();

private:
  presonus::trial08::FxRecallServices &services;
  Core::Portable::Parameter &slot, &loaded, &typeName, &presetName, &type;
  Core::CString64 category;
  int effectSlot;
};
} // namespace Presonus::Panel
