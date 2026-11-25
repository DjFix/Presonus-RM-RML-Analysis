#pragma once
#include "presonus/surface_panel/LEDState.hpp"

// Partial portable source class. Original declarations, layout and ARM ABI
// remain limited to the existing evidence; this migration adds no ABI claim.
namespace Presonus::Panel {
class SPIControl : public LEDControl {
public:
  explicit SPIControl(int tag);
  SPIControl(int tag, int group, int match);
  ~SPIControl() override;
  // Source-port void return; original unencoded declaration remains pending.
  void broadcastValue(int value) override;
};
} // namespace Presonus::Panel
