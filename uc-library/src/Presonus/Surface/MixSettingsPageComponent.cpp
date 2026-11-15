#include "presonus/surface/MixSettingsPageComponent.hpp"
#include <cstring>
namespace Presonus::Surface {
void MixSettingsPageComponent::paramChanged(Core::Portable::Parameter *p,
                                            int message) {
  Component::paramChanged(p, message);
  if (message != 3 || std::strcmp(p->getName(), "busdelay") != 0)
    return;
  auto *destination = getParameterByTag(1000);
  destination->setValue(p->getMax() > 0.f ? 1.f : 0.f, false);
}
} // namespace Presonus::Surface
