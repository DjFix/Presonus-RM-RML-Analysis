#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/gui/corecontrols.h"
#include "core/public/corevector.h"
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
  // Independent raw-allocation ownership model. Native elements are scalar
  // deleted then the Core vector is destroyed; original element type
  // unresolved.
  class Ranges {
  public:
    struct SourcePortTag {};
    struct Range;
    explicit Ranges(SourcePortTag) {}
    bool adoptRawAllocation(void *p) {
      return values_.add(static_cast<Range *>(p));
    }

  private:
    Core::Vector<Range *> values_;

  public:
    ~Ranges();
  };
  explicit MeterScaleControl(const Core::Rect &);
  ~MeterScaleControl() override;
  void adoptScaleInterpolator(std::unique_ptr<Core::Interpolator> p) {
    scale_ = std::move(p);
  }
  // Independent setup for the observed native tick sequence.
  void setPortableScaleTicks(std::vector<int> ticks) {
    ticks_ = std::move(ticks);
  }
  void draw(const Core::Portable::DrawEvent &) override;
  bool hasScaleInterpolator() const { return bool(scale_); }
  int scaleState() const { return scaleState_; }

private:
  std::unique_ptr<Core::Interpolator> scale_;
  int scaleState_ = 0;
  std::vector<int> ticks_;
};
} // namespace Presonus
