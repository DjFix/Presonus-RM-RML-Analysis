#pragma once
#include "presonus/panel/control.hpp"
#include <array>
#include <cstdint>

namespace presonus::panel_binding {
struct DigitalPotEndpoint {
  void *context = nullptr;
  // Independent synchronous boundary for the three initialized message bytes.
  void (*writePrefix)(void *, const std::array<std::uint8_t, 3> &) = nullptr;
};
struct DigitalPotState {
  int value = 0;
  int tag = 0;
  DigitalPotEndpoint *endpoint = nullptr;
  void *context = nullptr;
  // Required for paramChanged; original Control base body is not reconstructed.
  void (*baseParamChanged)(void *, Core::Portable::Parameter *, int) = nullptr;
};
} // namespace presonus::panel_binding

namespace Presonus::Panel {
// Portable source port with genuine Control cleanup. Layout, vtable ABI and
// unencoded ordinary return declarations remain unresolved.
class DigitalPotControl : public Control {
public:
  explicit DigitalPotControl(int tag);
  explicit DigitalPotControl(presonus::panel_binding::DigitalPotState &state)
      : Control(state.tag), borrowedState_(&state) {}
  ~DigitalPotControl() override;
  void paramChanged(Core::Portable::Parameter *parameter, int mode) override;
  void broadcastValue(int value) override;
  void transmit() override;

private:
  presonus::panel_binding::DigitalPotState &state() {
    return borrowedState_ ? *borrowedState_ : ownedState_;
  }

  presonus::panel_binding::DigitalPotState ownedState_;
  presonus::panel_binding::DigitalPotState *const borrowedState_ = nullptr;
};
} // namespace Presonus::Panel
