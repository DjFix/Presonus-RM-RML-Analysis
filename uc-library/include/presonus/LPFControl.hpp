#pragma once

#include "core/portable/gui/corecontrols.h"

// Portable CCL source port. The native Slider family is supported by the ELF
// vtable. The legacy view, parameter and destructor layouts remain distinct.
class LPFControl : public Core::Portable::Slider {
public:
  using Slider::Slider;
  ~LPFControl() override;
  void draw(const Core::Portable::DrawEvent &) override;
};
