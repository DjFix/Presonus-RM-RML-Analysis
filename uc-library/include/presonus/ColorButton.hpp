#pragma once

#include "core/portable/gui/corecontrols.h"

// Isolated CCL source port. The constructor provides borrowed parameter
// bindings for this portable model. Original declarations and ARM layout are
// unresolved.
class ColorButton : public Core::Portable::Control {
public:
  ColorButton(Core::RectRef size, Core::Portable::Parameter *parameter,
              Core::Portable::Parameter *colorParameter)
      : Core::Portable::Control(size, parameter),
        colorParameter_(colorParameter) {}

  void paramChanged(Core::Portable::Parameter *parameter, int message) override;

private:
  Core::Portable::Parameter *colorParameter_;
};
