#include "presonus/surface/CalibrateTouchComponent.hpp"
namespace Presonus::Surface {
CalibrateTouchComponent::CalibrateTouchComponent(const char *formName, int tag)
    : PageComponent("calibrateTouchPage", formName, tag) {}
CalibrateTouchComponent::~CalibrateTouchComponent() = default;
} // namespace Presonus::Surface
