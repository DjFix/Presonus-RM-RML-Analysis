#include "presonus/surface/StChannelSettingsPageComponent.hpp"
#include <cstring>
namespace Presonus::Surface {
void StChannelSettingsPageComponent::paramChanged(
    Core::Portable::Parameter *parameter, int message) {
  Core::Portable::Component::paramChanged(parameter, message);
  if (message != 3)
    return;
  const char *name = parameter->getName();
  if (std::strcmp(name ? name : "", "ch_select"))
    return;
  auto *original = parameter->getOriginal();
  if (!original)
    return;
  auto *controller = original->getController();
  if (!controller)
    return;
  // Intentional adaptation of original C++ RTTI to pinned CCL's actual type
  // IDs.
  auto *component =
      Core::Portable::core_cast<Core::Portable::Component>(controller);
  if (!component)
    return;
  const bool available = component->getParameterByTag(360) != nullptr;
  // Native has no null guard: source-port domain requires destination tag1000.
  getParameterByTag(1000)->setValue(available ? 1.f : 0.f, true);
}
} // namespace Presonus::Surface
