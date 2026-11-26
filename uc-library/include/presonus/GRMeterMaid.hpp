#pragma once
#include "presonus/MeterMaid.hpp"
namespace Presonus {
// Portable source port; original ARM object layout remains unresolved.
class GRMeterMaid : public MeterMaid {
public:
  GRMeterMaid();
  ~GRMeterMaid() override;
  float setLevel(float) override;
};
} // namespace Presonus
