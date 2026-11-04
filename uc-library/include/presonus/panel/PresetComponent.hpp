#pragma once

#include "core/portable/coreattributes.h"
#include "core/portable/corecomponent.h"
#include "core/portable/corefile.h"
#include "core/portable/corefilename.h"
#include "core/public/corestringbuffer.h"
#include "core/public/corevector.h"
#include "presonus/panel/PresetNameCache.hpp"

namespace presonus::panel {
class PresetApplicationServices;
struct PresetTestAccess;
} // namespace presonus::panel

namespace Presonus::Panel {
class PresetNameCache;

// Portable source contract. Original inheritance, fields, return declarations,
// ownership and ARM ABI remain unresolved. Core uses the pinned source
// provider.
class PresetComponent : public Core::Portable::Component {
public:
  class StorageCompletionHandler;
  struct Delegate; // Original callback object stays opaque.

  explicit PresetComponent(
      presonus::panel::PresetApplicationServices &services);
  ~PresetComponent() override;
  // Explicit independent registration token, not original subobject layout.
  void sourcePortObserveCache(PresetNameCache::Delegate *);
  // Ordinary return spellings are source-port contracts, not ELF declarations.
  int getSlotNum() const;
  Core::Portable::FileIOCompletionHandler *createStorageHandler() const;
  void doPresetSave(const char *, const char *,
                    const Core::Portable::Attributes &) const;
  void cacheUpdated(PresetNameCache &, int, const char *, const char *);
  void paramChanged(Core::Portable::Parameter *parameter, int message) override;
  virtual void updatePresetName() const;
  void presetStored() const;
  PresetNameCache *getCache() const;
  // Aggregate return is a portable declaration; original spelling unresolved.
  Core::Portable::FileName getFileNameForSlot(unsigned int) const;
  // Boolean source-port declaration; original return spelling remains
  // unresolved.
  bool isSlotEmpty(unsigned int) const;
  void updateEditName() const;
  bool getCurrentPresetName(Core::CStringBuffer<128> &name) const;
  int recall();
  void removeDelegate(Delegate *delegate);
  void presetRecalled() const;
  void addDelegate(Delegate *delegate);

private:
  friend struct presonus::panel::PresetTestAccess;
  presonus::panel::PresetApplicationServices &services;
  Core::Vector<Delegate *> delegates;
  PresetNameCache::Delegate *cacheObserver = nullptr;
};
} // namespace Presonus::Panel

namespace presonus::panel {
// Required independent application boundaries, not recovered original class
// declarations. No default implementation or fabricated cache/manager is used.
class PresetApplicationServices {
public:
  virtual ~PresetApplicationServices() = default;
  virtual int selectedSlot(const Presonus::Panel::PresetComponent &) const = 0;
  virtual bool slotEmpty(const Presonus::Panel::PresetComponent &,
                         unsigned slot) const = 0;
  virtual void slotFileName(Core::CString256 &,
                            const Presonus::Panel::PresetComponent &,
                            unsigned slot) const = 0;
  virtual const char *
  presetFolder(const Presonus::Panel::PresetComponent &) const = 0;
  virtual void ensureNameManager() const = 0;
  virtual Presonus::Panel::PresetNameCache *
  lookupCache(const char *folder) const = 0;
  virtual bool
  hasSelectedSlotParameter(const Presonus::Panel::PresetComponent &) const = 0;
  virtual void presetInfo(Core::CString64 &name, Core::CString32 &category,
                          int slot, const char *folder) const = 0;
  virtual const char *emptyNameMarker() const = 0;
  virtual void updateSelection(Presonus::Panel::PresetComponent &) = 0;
  virtual int recallAttributes(Presonus::Panel::PresetComponent &,
                               Core::Portable::Attributes &, bool edit) = 0;
  virtual void notifyDelegate(Presonus::Panel::PresetComponent::Delegate *,
                              const Presonus::Panel::PresetComponent &,
                              int slot, bool stored) const = 0;
};
} // namespace presonus::panel
