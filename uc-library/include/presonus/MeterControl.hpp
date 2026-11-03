#pragma once

#include "core/portable/gui/corecontrols.h"

namespace Presonus {
// Portable source port on CCL 5.0.0. These fields are deliberate host state,
// not a recovered original class layout. Constructors, ownership, and original
// unencoded return declarations remain unresolved; ARM interoperability
// unclaimed.
class MeterControl : public Core::Portable::Control {
public:
  using Control::Control;
  // Portable bool contract; original unencoded return declaration unresolved.
  bool isHorizontal() const;
  Core::Rect getLitRect(float value) const;
  Core::Rect getPeakRect(float value) const;
  Core::Rect subtractRect(const Core::Rect &a, const Core::Rect &b) const;
  int normalizedToPixel(float value) const;
  void setValue(float value);
  void setPeakValue(float value);
  void setPeakParameter(Core::Portable::Parameter *p);
  void paramChanged(Core::Portable::Parameter *p, int msg) override;
  void onIdle() override;
  void draw(const Core::Portable::DrawEvent &e) override;

protected:
  // Configuration/lifecycle are supplied by the hosting application. No native
  // constructor/destructor or interpolator ownership is asserted by this port.
  Core::Interpolator *interpolator = nullptr;
  Core::Portable::Parameter *peakParameter = nullptr;
  bool reverse = false;
  bool immediate = false;
  bool hidePeak = false;
  float value = 0;
  float drawnValue = 0;
  float peak = 0;
  float drawnPeak = 0;
  Core::Rect valueDirty, peakDirty;
  // Independent portable helper interpreting supplied neighbor instructions as
  // height > width. This does not reconstruct or export original isVertical.
  bool portableIsVertical() const;
};
} // namespace Presonus
