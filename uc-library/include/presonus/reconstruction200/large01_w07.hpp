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
class SurfaceInputComponent : public SurfaceChannelComponent {
public:
  ~SurfaceInputComponent() override;
  std::uint32_t levelAdjustable();
  std::uint32_t lookupPotSetting(float value);
};
class SurfaceOutputComponent : public SurfaceChannelComponent {
public:
  std::uint32_t levelAdjustable();
};
class ScribbleStripController {
public:
  virtual ~ScribbleStripController();
};
} // namespace Presonus::Surface
