#pragma once
#include "presonus/surface/SurfaceChannelComponent.hpp"
#include <cstdint>
namespace Presonus::Surface {
class SurfaceInputComponent : public SurfaceChannelComponent {
public:
  ~SurfaceInputComponent() override;
  // Provisional source-port returns; original return declaration remains
  // unresolved.
  Core::Portable::Parameter *getLevel() const;
  Core::Portable::Parameter *getPotValue() const;
  std::uint32_t levelAdjustable();
  std::uint32_t setLevel(float value);
  std::uint32_t lookupPotSetting(float value);
};
} // namespace Presonus::Surface
