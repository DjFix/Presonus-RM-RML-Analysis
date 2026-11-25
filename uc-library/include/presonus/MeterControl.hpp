#pragma once

#include "core/portable/gui/corecontrols.h"
#include "core/public/coreinterpolator.h"
#include <memory>

namespace Presonus {
// Portable source port on CCL 5.0.0. These fields are deliberate host state,
// not a recovered original class layout. Original field ownership and
// unencoded ordinary return declarations remain unresolved; ARM
// interoperability unclaimed.
class MeterControl : public Core::Portable::Control {
public:
  using Control::Control;
  explicit MeterControl(const Core::Rect &);
  ~MeterControl() override;
  void connect(void *) override;
  void setAttributes(const Core::Portable::Attributes &attributes) override;
  // Portable bool contract; original unencoded return declaration unresolved.
  bool isHorizontal() const;
  bool isVertical() const;
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
  // Subclasses may supply a borrowed interpolator. Attribute-created
  // interpolators have a separate owner.
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
  bool portableIsVertical() const;

private:
  std::unique_ptr<Core::Interpolator> ownedInterpolator;
};
} // namespace Presonus
