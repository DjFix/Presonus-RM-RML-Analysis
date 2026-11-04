#pragma once
#include "presonus/panel/control.hpp"

// Partial portable source class. Original declarations, layout and ARM ABI
// remain limited to the existing evidence; this migration adds no ABI claim.
namespace Presonus::Panel {
class SPIControl : public Control {
public:
  using Control::Control;
  ~SPIControl() override;
};
} // namespace Presonus::Panel
