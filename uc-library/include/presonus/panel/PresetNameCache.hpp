#pragma once
#include "core/portable/corefile.h"
#include "core/public/corevector.h"

namespace presonus::panel {
struct PresetCacheAccess;
}
namespace Presonus::Panel {
// Portable source port. Original fields, inheritance and return declarations
// remain unresolved; this class does not expose the original ARM layout.
class PresetNameCache {
public:
  struct Delegate;
  // Source-port state: named original scope; no original layout claim.
  struct CacheInfo {
    CacheInfo();
    Core::CString64 name;
    Core::CString32 category;
  };
  // Original return spelling is unresolved; int is the portable contract.
  int getCapacity() const;
  // Independent observer boundary; Delegate is intentionally opaque.
  struct ObserverSink {
    virtual ~ObserverSink() = default;
    virtual void changed(Delegate *, PresetNameCache &, int, const char *,
                         const char *) = 0;
    virtual void rebuilt(Delegate *, PresetNameCache &) = 0;
  };
  PresetNameCache(const char *type, const Core::Portable::FileName &folder,
                  int slots, int protectedSlots, ObserverSink &sink);
  bool parseFileName(const Core::Portable::FileName &,
                     Core::CStringBuffer<64> &, Core::CStringBuffer<32> &,
                     int &);
  static Core::Portable::FileName
  buildFileName(unsigned, const Core::Portable::FileName &, const char *,
                const char *, const char *, const char *, bool);
  Core::Portable::FileName buildFileName(unsigned, const char *, const char *,
                                         const char *, bool) const;
  bool canDelete(int) const;
  void cachePreset(const char *, const char *, int);
  void rebuild();
  void addCategory(const char *);
  void addObserver(Delegate *);
  // Independent source-port API, not a recovered original interface.
  // Removes the first matching borrowed registration through actual CCL
  // storage.
  void sourcePortRemoveObserver(Delegate *observer);
  bool getPresetInfo(Core::CStringBuffer<64> &, Core::CStringBuffer<32> &, int);
  Core::Portable::FileName getFileNameForSlot(unsigned, bool);

private:
  friend class PresetNameManager;
  friend struct presonus::panel::PresetCacheAccess;
  using Entry = CacheInfo;
  Core::CString64 type;
  Core::Portable::FileName folder;
  bool dirty = true;
  int protectedSlots;
  int capacity;
  Core::Vector<Delegate *> observers;
  Core::Vector<Entry> entries;
  Core::Vector<Core::CString32> categories;
  ObserverSink &sink;
};
} // namespace Presonus::Panel
