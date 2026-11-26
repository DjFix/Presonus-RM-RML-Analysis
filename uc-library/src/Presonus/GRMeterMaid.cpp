#include "presonus/GRMeterMaid.hpp"
namespace Presonus {
GRMeterMaid::GRMeterMaid() : MeterMaid(DecayTablePolicy::None) {}
GRMeterMaid::~GRMeterMaid() = default;
float GRMeterMaid::setLevel(float value) {
  return MeterBallistics::setLevel(1.f - value);
}
} // namespace Presonus
