#pragma once
#include "core/public/corevector.h"
#include "presonus/uc/ServerComponent.hpp"
#include <array>
#include <utility>
#include <vector>
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
  struct AutoGroupingState {
    // Borrowed category groups in the original preset category order.
    std::array<Core::Portable::Component *, 9> groups{};
    // The original constructor's first encoded integer supplies the ordinal.
    std::vector<std::pair<ChannelComponent *, int>> channelOrdinals;
  };
  void bindAutoGrouping(const AutoGroupingState &state) {
    autoGrouping_ = &state;
  }
  // Portable void declarations. The original unencoded declaration is pending.
  void updateAutoGroup(ChannelComponent *);
  void onIdle() override;
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
  const AutoGroupingState *autoGrouping_ = nullptr;
  Core::Vector<ChannelComponent *> updateChannels_;
  Core::Vector<Core::Portable::Component *> ownedComponents_;
};
} // namespace Presonus::Mixer
