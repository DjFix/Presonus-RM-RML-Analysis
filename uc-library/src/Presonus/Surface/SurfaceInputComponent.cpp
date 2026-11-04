#include "presonus/surface/SurfaceInputComponent.hpp"
#include <cmath>
namespace {
// Exact binary64 values from the hash-bound original gMicGainMap payload.
constexpr double gainMap[] = {
    0x1.4828f5c28f5c3p+5, 0x1.25851eb851eb8p+5, 0x1.107ae147ae148p+5,
    0x1.ff33333333333p+4, 0x1.e59999999999ap+4, 0x1.cf0a3d70a3d71p+4,
    0x1.bcccccccccccdp+4, 0x1.abd70a3d70a3dp+4, 0x1.9d9999999999ap+4,
    0x1.9000000000000p+4, 0x1.847ae147ae148p+4, 0x1.7947ae147ae14p+4,
    0x1.6f851eb851eb8p+4, 0x1.66147ae147ae1p+4, 0x1.5d9999999999ap+4,
    0x1.5547ae147ae14p+4, 0x1.4e66666666666p+4, 0x1.46b851eb851ecp+4,
    0x1.4028f5c28f5c3p+4, 0x1.399999999999ap+4, 0x1.33ae147ae147bp+4,
    0x1.2dc28f5c28f5cp+4, 0x1.287ae147ae148p+4, 0x1.230a3d70a3d71p+4,
    0x1.1e147ae147ae1p+4, 0x1.191eb851eb852p+4, 0x1.14a3d70a3d70ap+4,
    0x1.1028f5c28f5c3p+4, 0x1.0c00000000000p+4, 0x1.07d70a3d70a3dp+4,
    0x1.0400000000000p+4, 0x1.0000000000000p+4, 0x1.f947ae147ae14p+3,
    0x1.f19999999999ap+3, 0x1.eae147ae147aep+3, 0x1.e3d70a3d70a3dp+3,
    0x1.dd70a3d70a3d7p+3, 0x1.d70a3d70a3d71p+3, 0x1.d0f5c28f5c28fp+3,
    0x1.cae147ae147aep+3, 0x1.c570a3d70a3d7p+3, 0x1.bf5c28f5c28f6p+3,
    0x1.ba3d70a3d70a4p+3, 0x1.b4ccccccccccdp+3, 0x1.afae147ae147bp+3,
    0x1.aa8f5c28f5c29p+3, 0x1.a570a3d70a3d7p+3, 0x1.a0a3d70a3d70ap+3,
    0x1.9c28f5c28f5c3p+3, 0x1.975c28f5c28f6p+3, 0x1.92e147ae147aep+3,
    0x1.8e66666666666p+3, 0x1.8a3d70a3d70a4p+3, 0x1.8000000000000p+3,
    0x1.86147ae147ae1p+3, 0x1.7dc28f5c28f5cp+3, 0x1.79eb851eb851fp+3,
    0x1.76147ae147ae1p+3, 0x1.723d70a3d70a4p+3, 0x1.6e66666666666p+3,
    0x1.6ae147ae147aep+3, 0x1.670a3d70a3d71p+3, 0x1.63851eb851eb8p+3,
    0x1.6000000000000p+3, 0x1.5cccccccccccdp+3, 0x1.599999999999ap+3,
    0x1.5666666666666p+3, 0x1.54ccccccccccdp+3, 0x1.5000000000000p+3,
    0x1.4cccccccccccdp+3, 0x1.499999999999ap+3, 0x1.46b851eb851ecp+3,
    0x1.4333333333333p+3, 0x1.40f5c28f5c28fp+3, 0x1.3e147ae147ae1p+3,
    0x1.3b851eb851eb8p+3, 0x1.38a3d70a3d70ap+3, 0x1.399999999999ap+3,
    0x1.3333333333333p+3, 0x1.30f5c28f5c28fp+3, 0x1.2e66666666666p+3,
    0x1.399999999999ap+3, 0x1.2947ae147ae14p+3, 0x1.26b851eb851ecp+3,
    0x1.2428f5c28f5c3p+3, 0x1.21eb851eb851fp+3, 0x1.1f5c28f5c28f6p+3,
    0x1.1d1eb851eb852p+3, 0x1.1ae147ae147aep+3, 0x1.18a3d70a3d70ap+3,
    0x1.1666666666666p+3, 0x1.1428f5c28f5c3p+3, 0x1.11eb851eb851fp+3,
    0x1.1000000000000p+3, 0x1.0dc28f5c28f5cp+3, 0x1.0c28f5c28f5c3p+3,
    0x1.099999999999ap+3, 0x1.07ae147ae147bp+3, 0x1.0570a3d70a3d7p+3,
    0x1.03851eb851eb8p+3, 0x1.019999999999ap+3, 0x1.ff5c28f5c28f6p+2,
    0x1.fc28f5c28f5c3p+2, 0x1.f7ae147ae147bp+2, 0x1.ed70a3d70a3d7p+2,
    0x1.e99999999999ap+2, 0x1.ec28f5c28f5c3p+2, 0x1.e851eb851eb85p+2,
    0x1.e51eb851eb852p+2, 0x1.e1eb851eb851fp+2, 0x1.deb851eb851ecp+2,
    0x1.db851eb851eb8p+2, 0x1.d851eb851eb85p+2, 0x1.d47ae147ae148p+2,
    0x1.ccccccccccccdp+2, 0x1.ccccccccccccdp+2, 0x1.ca3d70a3d70a4p+2,
    0x1.c70a3d70a3d71p+2, 0x1.c47ae147ae148p+2, 0x1.c000000000000p+2,
    0x1.c000000000000p+2, 0x1.bae147ae147aep+2, 0x1.b666666666666p+2,
    0x1.b333333333333p+2, 0x1.b1eb851eb851fp+2, 0x1.acccccccccccdp+2,
    0x1.acccccccccccdp+2, 0x1.a8f5c28f5c28fp+2, 0x1.a666666666666p+2,
    0x1.a333333333333p+2, 0x1.a0a3d70a3d70ap+2, 0x1.9cccccccccccdp+2,
    0x1.9cccccccccccdp+2, 0x1.9851eb851eb85p+2, 0x1.9333333333333p+2,
    0x1.9333333333333p+2, 0x1.90a3d70a3d70ap+2, 0x1.8cccccccccccdp+2,
    0x1.8cccccccccccdp+2, 0x1.88f5c28f5c28fp+2, 0x1.8666666666666p+2,
    0x1.83d70a3d70a3dp+2, 0x1.8147ae147ae14p+2, 0x1.7eb851eb851ecp+2,
    0x1.7cccccccccccdp+2, 0x1.7cccccccccccdp+2, 0x1.77ae147ae147bp+2,
    0x1.751eb851eb852p+2, 0x1.751eb851eb852p+2, 0x1.70a3d70a3d70ap+2,
    0x1.6cccccccccccdp+2, 0x1.699999999999ap+2, 0x1.699999999999ap+2,
    0x1.67ae147ae147bp+2, 0x1.699999999999ap+2, 0x1.699999999999ap+2,
    0x1.60a3d70a3d70ap+2, 0x1.5cccccccccccdp+2, 0x1.5cccccccccccdp+2,
    0x1.5cccccccccccdp+2, 0x1.5851eb851eb85p+2, 0x1.5851eb851eb85p+2,
    0x1.5851eb851eb85p+2, 0x1.5851eb851eb85p+2, 0x1.5000000000000p+2,
    0x1.5000000000000p+2, 0x1.5000000000000p+2, 0x1.5000000000000p+2,
    0x1.4851eb851eb85p+2, 0x1.4851eb851eb85p+2, 0x1.4851eb851eb85p+2,
    0x1.4851eb851eb85p+2, 0x1.40a3d70a3d70ap+2, 0x1.40a3d70a3d70ap+2,
    0x1.40a3d70a3d70ap+2, 0x1.40a3d70a3d70ap+2, 0x1.399999999999ap+2,
    0x1.399999999999ap+2, 0x1.399999999999ap+2, 0x1.399999999999ap+2,
    0x1.31eb851eb851fp+2, 0x1.31eb851eb851fp+2, 0x1.31eb851eb851fp+2,
    0x1.31eb851eb851fp+2, 0x1.2ae147ae147aep+2, 0x1.2ae147ae147aep+2,
    0x1.2ae147ae147aep+2, 0x1.2ae147ae147aep+2, 0x1.247ae147ae148p+2,
    0x1.247ae147ae148p+2, 0x1.247ae147ae148p+2, 0x1.247ae147ae148p+2,
    0x1.247ae147ae148p+2, 0x1.1c28f5c28f5c3p+2, 0x1.1c28f5c28f5c3p+2,
    0x1.1c28f5c28f5c3p+2, 0x1.1c28f5c28f5c3p+2, 0x1.15c28f5c28f5cp+2,
    0x1.15c28f5c28f5cp+2, 0x1.15c28f5c28f5cp+2, 0x1.15c28f5c28f5cp+2,
    0x1.15c28f5c28f5cp+2, 0x1.0e147ae147ae1p+2, 0x1.0e147ae147ae1p+2,
    0x1.0e147ae147ae1p+2, 0x1.0e147ae147ae1p+2, 0x1.0e147ae147ae1p+2,
    0x1.0666666666666p+2, 0x1.0666666666666p+2, 0x1.0666666666666p+2,
    0x1.0666666666666p+2, 0x1.00a3d70a3d70ap+2, 0x1.00a3d70a3d70ap+2,
    0x1.00a3d70a3d70ap+2, 0x1.00a3d70a3d70ap+2, 0x1.00a3d70a3d70ap+2,
    0x1.f333333333333p+1, 0x1.f333333333333p+1, 0x1.f333333333333p+1,
    0x1.f333333333333p+1, 0x1.f333333333333p+1, 0x1.e666666666666p+1,
    0x1.e666666666666p+1, 0x1.e666666666666p+1, 0x1.e666666666666p+1,
    0x1.e666666666666p+1, 0x1.e666666666666p+1, 0x1.d70a3d70a3d71p+1,
    0x1.d70a3d70a3d71p+1, 0x1.d70a3d70a3d71p+1, 0x1.d70a3d70a3d71p+1,
    0x1.d70a3d70a3d71p+1, 0x1.ca3d70a3d70a4p+1, 0x1.ca3d70a3d70a4p+1,
    0x1.ca3d70a3d70a4p+1, 0x1.ca3d70a3d70a4p+1, 0x1.ca3d70a3d70a4p+1,
    0x1.beb851eb851ecp+1, 0x1.beb851eb851ecp+1, 0x1.beb851eb851ecp+1,
    0x1.beb851eb851ecp+1, 0x1.beb851eb851ecp+1, 0x1.beb851eb851ecp+1,
    0x1.b0a3d70a3d70ap+1, 0x1.b0a3d70a3d70ap+1, 0x1.b0a3d70a3d70ap+1,
    0x1.b0a3d70a3d70ap+1, 0x1.b0a3d70a3d70ap+1, 0x1.b0a3d70a3d70ap+1,
    0x1.a28f5c28f5c29p+1, 0x1.a28f5c28f5c29p+1, 0x1.a28f5c28f5c29p+1,
    0x1.a28f5c28f5c29p+1, 0x1.a28f5c28f5c29p+1, 0x1.a28f5c28f5c29p+1,
    0x1.95c28f5c28f5cp+1};
} // namespace
namespace Presonus::Surface {
SurfaceInputComponent::~SurfaceInputComponent() = default;
std::uint32_t SurfaceInputComponent::levelAdjustable() {
  return channelMode == 0;
}
std::uint32_t SurfaceInputComponent::lookupPotSetting(float value) {
  float best = 100.0f;
  std::uint32_t result = 0;
  for (std::uint32_t i = 0; i < 256; ++i) {
    const float distance = std::fabs(value - static_cast<float>(gainMap[i]));
    if (distance < best) {
      best = distance;
      result = i;
    }
  }
  return result;
}
} // namespace Presonus::Surface
