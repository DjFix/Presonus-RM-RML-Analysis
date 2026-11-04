#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/gui/corecontrols.h"
#include "presonus/delay_timer.hpp"
#include "presonus/uc/client_implementation.hpp"
#include "presonus/uc/client_typed_origins.hpp"
#include <memory>
#include <vector>
namespace Presonus {
// Independent host state selected from observed constructor zeroing and virtual
// cleanup. No original member declarations, inheritance or ARM layout asserted.
class MeterScaleControl : public Core::Portable::Control {
public:
  explicit MeterScaleControl(const Core::Rect &);
  ~MeterScaleControl() override;
  void adoptScaleInterpolator(std::unique_ptr<Core::Interpolator> p) {
    scale_ = std::move(p);
  }
  bool hasScaleInterpolator() const { return bool(scale_); }
  int scaleState() const { return scaleState_; }

private:
  std::unique_ptr<Core::Interpolator> scale_;
  int scaleState_ = 0;
};
} // namespace Presonus
