#pragma once
#include "core/public/coreinterpolator.h"
namespace presonus::dsp {
// Independent modern source port; NOT Core::LogInterpolator or its ARM ABI.
// Seven strict EQ/filter domains plus observed Gate [40,16000]/mid0.
// Gate alone accepts raw20..40 at inverse input, using actual CCL linear clamp
// in logarithmic space. This preserves rawdefault20 but is noninjective:
// 20 -> normalized0 -> 40. No original CoreLog equivalence is claimed.
class EqLogSourceInterpolator final : public Core::Interpolator {
public:
  EqLogSourceInterpolator();
  ~EqLogSourceInterpolator() override;
  void setRange(float minimum, float maximum, float midpoint = 0.f) override;
  float normalizedToRange(float normalized) const override;
  float rangeToNormalized(float value) const override;
  bool sourceRangeSupported() const noexcept { return supported_; }

private:
  Core::LinearInterpolator logarithmicDomain_;
  bool supported_ = false;
};
// Explicit bootstrap only, before concurrent registry use. No automatic startup
// registration. Conflicting names and unsupported domains fail explicitly.
void registerEqSourcePortProviders();
bool eqSourcePortProvidersReady() noexcept;
} // namespace presonus::dsp
