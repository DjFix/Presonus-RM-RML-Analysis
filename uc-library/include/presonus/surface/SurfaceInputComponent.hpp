#pragma once
#include "presonus/surface/SurfaceChannelComponent.hpp"
#include <cstdint>
namespace Presonus::Surface {
class SurfaceInputComponent : public SurfaceChannelComponent {
public:
  ~SurfaceInputComponent() override;
  std::uint32_t levelAdjustable();
  std::uint32_t lookupPotSetting(float value);
};
} // namespace Presonus::Surface
