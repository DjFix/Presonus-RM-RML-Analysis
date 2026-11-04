#pragma once
#include "core/portable/corecomponent.h"
#include <cstdint>
namespace Presonus::Surface {
// Portable source model; these fields do not assert original ARM layout.
class SurfaceChannelComponent : public Core::Portable::Component {
public:
  ~SurfaceChannelComponent() override;
  std::uint32_t channelMode = 0;
};
} // namespace Presonus::Surface
