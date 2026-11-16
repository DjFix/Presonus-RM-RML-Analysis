#pragma once
#include "core/portable/corecomponent.h"
namespace presonus::surface {
struct CalibrateTouchInit {};
} // namespace presonus::surface
namespace Presonus::Surface {
// Partial source port over real CCL. Original base layout/ABI remains unknown.
class CalibrateTouchComponent : public Core::Portable::Component {
public:
  explicit CalibrateTouchComponent(presonus::surface::CalibrateTouchInit)
      : Core::Portable::Component("portable calibration") {}
  ~CalibrateTouchComponent() override;
};
} // namespace Presonus::Surface
