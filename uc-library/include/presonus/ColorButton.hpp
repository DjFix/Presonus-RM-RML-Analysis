#pragma once

#include "core/portable/gui/corecontrols.h"

// Isolated CCL source port. The constructor provides borrowed parameter
// bindings for this portable model. Original declarations and ARM layout are
// unresolved.
namespace Presonus {
class MixerClientComponentBase;
}

class ColorButton : public Core::Portable::Control {
public:
  ColorButton(Core::RectRef size, Core::Portable::Parameter *parameter,
              Core::Portable::Parameter *colorParameter)
      : Core::Portable::Control(size, parameter),
        colorParameter_(colorParameter) {}

  void draw(const Core::Portable::DrawEvent &event) override;
  // Source-port render inputs are borrowed. The original field layout is
  // unresolved.
  void bindDrawingSources(const Presonus::MixerClientComponentBase *mixer,
                          Core::Portable::Bitmap *fallbackBitmap = nullptr) {
    mixer_ = mixer;
    fallbackBitmap_ = fallbackBitmap;
  }

  void paramChanged(Core::Portable::Parameter *parameter, int message) override;

private:
  Core::Portable::Parameter *colorParameter_;
  const Presonus::MixerClientComponentBase *mixer_ = nullptr;
  Core::Portable::Bitmap *fallbackBitmap_ = nullptr;
};
