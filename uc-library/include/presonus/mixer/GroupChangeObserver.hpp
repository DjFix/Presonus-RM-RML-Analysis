#pragma once

#include "core/portable/corecomponent.h"

namespace Presonus::Mixer {
class ChannelComponent;
class AutoFilterGroupManager;
// Partial portable source port. Original ARM layout, intermediate inheritance,
// exception cleanup and complete destructor behavior are not established.
// Channel and manager are borrowed and must outlive this observer. The observed
// parameter may die first: its real kDestroyed notification detaches us.
class GroupChangeObserver : public Core::Portable::Component {
public:
  GroupChangeObserver(ChannelComponent *, AutoFilterGroupManager &);
  ~GroupChangeObserver() override;
  GroupChangeObserver(const GroupChangeObserver &) = delete;
  GroupChangeObserver &operator=(const GroupChangeObserver &) = delete;
  void paramChanged(Core::Portable::Parameter *, int) override;
  // Independent source-port lifecycle API. Call before borrowed providers die;
  // destructor also detaches. It does not reconstruct an original ELF method.
  void detachSourcePortObserver();

private:
  ChannelComponent *channel_;
  AutoFilterGroupManager &manager_;
  Core::Portable::Parameter *observed_ = nullptr;
};
} // namespace Presonus::Mixer
