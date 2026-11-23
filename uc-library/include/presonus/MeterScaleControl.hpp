#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/gui/corecontrols.h"
#include "core/public/corestringbuffer.h"
#include "core/public/corevector.h"
#include "presonus/delay_timer.hpp"
#include "presonus/uc/client_implementation.hpp"
#include "presonus/uc/client_typed_origins.hpp"
#include <memory>
#include <vector>
namespace presonus::meter {
struct MeterScaleAttributeAccess;
}

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
    // Portable record. The original field declarations and layout are
    // unresolved.
    struct Range {
      const int *values; // Borrowed from the caller.
      int count;
      Core::CStringBuffer<128> name;
    };
    explicit Ranges(SourcePortTag) {}
    Ranges(const Ranges &) = delete;
    Ranges &operator=(const Ranges &) = delete;

    // Provisional portable declarations; original return types are unencoded.
    void addRange(const char *name, int count, const int *values);
    Range *getRange(const char *name);
    int count() const { return values_.count(); }
    const Range *at(int index) const {
      return values_.isValidIndex(index) ? values_.at(index) : nullptr;
    }
    // Storage from this lifecycle hook is only suitable for lookup if it
    // contains a constructed Range.
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
  void setAttributes(const Core::Portable::Attributes &) override;
  void draw(const Core::Portable::DrawEvent &) override;
  bool hasScaleInterpolator() const { return bool(scale_); }
  int scaleState() const { return scaleState_; }

private:
  friend struct presonus::meter::MeterScaleAttributeAccess;
  // The process-wide registry owns records and keeps their addresses stable.
  const Ranges::Range *range_ = nullptr;
  std::unique_ptr<Core::Interpolator> scale_;
  int scaleState_ = 0;
  std::vector<int> ticks_;
};
} // namespace Presonus

// Portable declaration for the original global C++ initializer.
void __initMeterScaleControl();

namespace presonus::meter {
// Read-only source-port access to the process-wide meter scale records.
const Presonus::MeterScaleControl::Ranges &sourcePortMeterScaleRanges();
} // namespace presonus::meter
