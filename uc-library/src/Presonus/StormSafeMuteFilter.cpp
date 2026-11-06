#include "presonus/StormMuteGroupComponent.hpp"
#include <cstring>

namespace Presonus {
bool StormMuteGroupComponent::SafeMuteFilter::shouldLoad(int typeId,
                                                         const char *,
                                                         void *object) const {
  if (typeId == Core::Portable::Component::kTypeID)
    return true;
  if (typeId != Core::Portable::Parameter::kTypeID || !object)
    return false;
  auto *parameter = static_cast<Core::Portable::Parameter *>(object);
  const char *name = parameter->getName();
  if (std::strcmp(name ? name : "", "mute") == 0)
    safeList.add(parameter);
  // Loading records membership without applying the stored parameter value.
  return false;
}
bool StormMuteGroupComponent::SafeMuteFilter::shouldSave(int typeId,
                                                         const char *,
                                                         void *object) const {
  if (typeId == Core::Portable::Component::kTypeID)
    return true;
  if (typeId != Core::Portable::Parameter::kTypeID || !object)
    return false;
  auto *parameter = static_cast<Core::Portable::Parameter *>(object);
  const char *name = parameter->getName();
  return std::strcmp(name ? name : "", "mute") == 0 &&
         safeList.contains(parameter);
}
} // namespace Presonus
