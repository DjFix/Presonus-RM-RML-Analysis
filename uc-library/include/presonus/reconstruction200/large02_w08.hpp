#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/gui/corecontrols.h"
#include "presonus/delay_timer.hpp"
#include "presonus/uc/client_implementation.hpp"
#include "presonus/uc/client_typed_origins.hpp"
#include <memory>
#include <vector>
namespace Presonus {
// Independent host state selected from observed constructor zeroing and virtual
// cleanup. No original member declarations, inheritance or ARM layout asserted.
class MeterScaleControl : public Core::Portable::Control {
public:
  explicit MeterScaleControl(const Core::Rect &);
  ~MeterScaleControl() override;
  void adoptScaleInterpolator(std::unique_ptr<Core::Interpolator> p) {
    scale_ = std::move(p);
  }
  bool hasScaleInterpolator() const { return bool(scale_); }
  int scaleState() const { return scaleState_; }

private:
  std::unique_ptr<Core::Interpolator> scale_;
  int scaleState_ = 0;
};
namespace Surface {
// Original-named partial source port. Host binds actual providers; pointers
// outlive this component. Timer count and tag ranges follow native
// instructions.
class MuteGroupsComponent : public Core::Portable::Component {
public:
  using Parameter = Core::Portable::Parameter;
  MuteGroupsComponent() = default;
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
  std::vector<DelayTimer *> timers_;
  DelayTimer refresh_{0.f};
  UC::ClientImplementation *client_ = nullptr;
  presonus::uc::ClientTypedOrigins *origins_ = nullptr;
  DelayTimer *timer(int i) const {
    return i >= 0 && i < int(timers_.size()) ? timers_[i] : nullptr;
  }
};
} // namespace Surface
} // namespace Presonus
