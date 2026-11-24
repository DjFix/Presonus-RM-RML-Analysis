#include "presonus/surface/PreampsPageComponent.hpp"
namespace Presonus::Surface {
PreampsPageComponent::PreampsPageComponent(const char *formName, int tag)
    : PageComponent("preamps", formName, tag) {}
PreampsPageComponent::~PreampsPageComponent() = default;
} // namespace Presonus::Surface
