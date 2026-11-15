#pragma once
#include "presonus/surface/SurfaceChannelComponent.hpp"
#include <cstdint>
namespace Presonus::Surface {
class SurfaceOutputComponent : public SurfaceChannelComponent {
public:
  std::uint32_t levelAdjustable();
  // Source-port pointer returns; original spelling/const qualification pending.
  Core::Portable::Parameter *getDacValue() const;
  Core::Portable::Parameter *getLevel() const;
};
} // namespace Presonus::Surface
