#pragma once
#include "presonus/PageComponent.hpp"
namespace presonus::surface {
struct CalibrateTouchInit {};
} // namespace presonus::surface
namespace Presonus::Surface {
class CalibrateTouchComponent : public PageComponent {
public:
  CalibrateTouchComponent(const char *formName, int tag);
  explicit CalibrateTouchComponent(presonus::surface::CalibrateTouchInit)
      : PageComponent("portable calibration", "", 0) {}
  ~CalibrateTouchComponent() override;
};
} // namespace Presonus::Surface
