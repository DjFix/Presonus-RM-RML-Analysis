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

  void setMeter(float) override;
  void setPeak(float) override;
  void setSignal(bool) override;
  void setClipped(bool) override;
  bool isClipped() const override;

  void bindParameters(Core::Portable::NumericParam *meter,
                      Core::Portable::NumericParam *peak) noexcept;
  void bindIndicatorParameters(Core::Portable::NumericParam *signal,
                               Core::Portable::NumericParam *clip) noexcept;

protected:
  explicit MeterMaid(DecayTablePolicy);

private:
  friend struct presonus::meter::MeterStateAccess;
  Core::Portable::NumericParam *meter_ = nullptr;
  Core::Portable::NumericParam *peak_ = nullptr;
  Core::Portable::NumericParam *signal_ = nullptr;
  Core::Portable::NumericParam *clip_ = nullptr;
};
} // namespace Presonus
