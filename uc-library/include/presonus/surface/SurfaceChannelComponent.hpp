#pragma once
#include "presonus/uc/ServerComponent.hpp"
#include <cstdint>
namespace Presonus::Surface {
// Portable source model; these fields do not assert original ARM layout.
class SurfaceChannelComponent : public UC::ServerComponent {
public:
  SurfaceChannelComponent();
  explicit SurfaceChannelComponent(int mode);
  ~SurfaceChannelComponent() override;
  std::uint32_t channelMode = 0;
};
} // namespace Presonus::Surface
