#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/gui/corecontrols.h"
#include "presonus/delay_timer.hpp"
#include "presonus/uc/client_implementation.hpp"
#include "presonus/uc/client_typed_origins.hpp"
#include <array>
#include <memory>
#include <vector>
namespace Presonus::Surface {
// Original-named partial source port. Explicitly bound providers and timers
// are borrowed and must outlive this component.
class MuteGroupsComponent : public Core::Portable::Component {
public:
  using Parameter = Core::Portable::Parameter;
  MuteGroupsComponent();
  ~MuteGroupsComponent() override;
  void paramChanged(Parameter *, int) override;
  void storeMuteGroup(int);
  void onIdle() override;
  void bindMuteTimers(std::vector<DelayTimer *> timers) {
    timers_ = std::move(timers);
  }
  void bindMuteClient(UC::ClientImplementation *client,
                      presonus::uc::ClientTypedOrigins *origins) {
    client_ = client;
    origins_ = origins;
  }
  DelayTimer &muteRefreshTimer() { return refresh_; }

private:
  std::array<std::unique_ptr<DelayTimer>, 8> ownedTimers_;
  std::vector<DelayTimer *> timers_;
  DelayTimer refresh_{0.1f};
  UC::ClientImplementation *client_ = nullptr;
  presonus::uc::ClientTypedOrigins *origins_ = nullptr;
  DelayTimer *timer(int i) const {
    return i >= 0 && i < int(timers_.size()) ? timers_[i] : nullptr;
  }
};
} // namespace Presonus::Surface
