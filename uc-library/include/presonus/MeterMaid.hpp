#pragma once

#include "presonus/MeterBallistics.hpp"

namespace Core::Portable {
class NumericParam;
}

namespace Presonus {
// Portable typed composition of the observed base and borrowed parameter slots.
// The original layout and ownership remain unresolved.
class MeterMaid : public MeterBallistics {
public:
  MeterMaid();
  ~MeterMaid() override;

  void setMeter(float);
  void setPeak(float);
  void setSignal(bool);
  void setClipped(bool);
  bool isClipped() const;

  void bindParameters(Core::Portable::NumericParam *meter,
                      Core::Portable::NumericParam *peak) noexcept;
  void bindIndicatorParameters(Core::Portable::NumericParam *signal,
                               Core::Portable::NumericParam *clip) noexcept;

private:
  friend struct presonus::meter::MeterStateAccess;
  Core::Portable::NumericParam *meter_ = nullptr;
  Core::Portable::NumericParam *peak_ = nullptr;
  Core::Portable::NumericParam *signal_ = nullptr;
  Core::Portable::NumericParam *clip_ = nullptr;
};
} // namespace Presonus
