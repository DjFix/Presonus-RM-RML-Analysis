#pragma once
#include "core/portable/coreparams.h"
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
// Partial source interface, not the original base hierarchy, storage or vtable
// ABI. Original unencoded return spellings remain declaration-pending.
class DigitalPotControl {
public:
  explicit DigitalPotControl(presonus::panel_binding::DigitalPotState &state)
      : state_(state) {}
  virtual void paramChanged(Core::Portable::Parameter *parameter, int mode);
  virtual void broadcastValue(int value);
  virtual void transmit();

private:
  presonus::panel_binding::DigitalPotState &state_;
};
} // namespace Presonus::Panel
