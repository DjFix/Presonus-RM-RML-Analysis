#pragma once
#include "core/public/corevector.h"
#include "presonus/uc/ServerComponent.hpp"
namespace Presonus::Mixer {
class ChannelComponent;
// Partial source port. No original inheritance, layout, constructor or return
// declaration is established. Entries are borrowed identities, never owned.
class AutoFilterGroupManager : public Presonus::UC::ServerComponent {
public:
  struct SourcePortConstruction {};
  explicit AutoFilterGroupManager(SourcePortConstruction, int capacity = 0,
                                  int delta = 5)
      : updateChannels_(capacity, delta) {}
  ~AutoFilterGroupManager() override;
  // Independent portable owner collection corresponding to native +0xa0.
  // Entries in updateChannels_ remain borrowed and are never deleted.
  Core::Vector<Core::Portable::Component *> &portableOwnedComponents() {
    return ownedComponents_;
  }
  // Native preserves null entries and duplicate pointers. Allocation failure
  // leaves the collection unchanged. void is a provisional declaration.
  void addUpdateChannel(ChannelComponent *);
  const Core::Vector<ChannelComponent *> &portableUpdateChannels() const {
    return updateChannels_;
  }

private:
  Core::Vector<ChannelComponent *> updateChannels_;
  Core::Vector<Core::Portable::Component *> ownedComponents_;
};
} // namespace Presonus::Mixer
