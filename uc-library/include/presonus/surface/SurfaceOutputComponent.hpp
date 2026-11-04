#pragma once
#include "presonus/surface/SurfaceChannelComponent.hpp"
#include <cstdint>
namespace Presonus::Surface {
class SurfaceOutputComponent : public SurfaceChannelComponent {
public:
  std::uint32_t levelAdjustable();
};
} // namespace Presonus::Surface
