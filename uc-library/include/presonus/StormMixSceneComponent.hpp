#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/delay_timer.hpp"
#include <cstdint>

namespace Presonus {
class StormMixSceneComponent;
}
namespace presonus::scene_port {
// Independent source-port boundaries. These are not recovered original classes,
// delegate declarations, ownership rules or ARM object layouts.
struct StoreDelegate {
  virtual ~StoreDelegate() = default;
  virtual void enter(Presonus::StormMixSceneComponent &) = 0;
  virtual void leave(Presonus::StormMixSceneComponent &) = 0;
};
// Fixture-only timer service. Production uses borrowed real DelayTimer objects.
struct Timer {
  virtual ~Timer() = default;
  virtual bool executing() const = 0;
  virtual bool longEnough() const = 0;
  virtual void end() = 0;
};
struct Recall {
  virtual ~Recall() = default;
  virtual bool recall(unsigned int index) const = 0;
};
} // namespace presonus::scene_port
namespace Presonus {
// Portable source binding to real CCL Component. Inheritance, member layout and
// unencoded return declarations are selected port contracts, not original ABI.
class StormMixSceneComponent : public Core::Portable::Component {
public:
  explicit StormMixSceneComponent(presonus::scene_port::Recall &recall)
      : recallBoundary(recall) {}
  bool isStoreOn() const;
  void enterStoreState(bool state);
  void setAllMixButtons(bool state);
  void doRecall(unsigned int index);
  void onIdle() override;
  // Independent port configuration/accessors; no original identity claimed.
  void configureStoreDelegate(presonus::scene_port::StoreDelegate *value) {
    delegate = value;
  }
  // Borrowed objects and backing array must remain alive/stable during idle.
  void configureTimers(Presonus::DelayTimer **value, unsigned int count) {
    timers = value;
    fixtureTimers = nullptr;
    timerCount = count;
  }
  // Explicit fixture boundary; does not configure production timer objects.
  void configureFixtureTimers(presonus::scene_port::Timer **value,
                              unsigned int count) {
    fixtureTimers = value;
    timers = nullptr;
    timerCount = count;
  }
  std::uint32_t recalledIndex() const { return selectedIndex; }

private:
  presonus::scene_port::Recall &recallBoundary;
  presonus::scene_port::StoreDelegate *delegate = nullptr;
  Presonus::DelayTimer **timers = nullptr;
  presonus::scene_port::Timer **fixtureTimers = nullptr;
  unsigned int timerCount = 0;
  std::uint32_t selectedIndex = UINT32_MAX;
};
} // namespace Presonus
