#include "core/portable/corecomponent.h"
#include "presonus/MuteGroupBase.hpp"
#include <cstring>

namespace Presonus {
bool MuteGroupBase::Filter::shouldLoad(int typeId, const char *,
                                       void *object) const {
  if (typeId == Core::Portable::Component::kTypeID)
    return true;
  if (typeId != Core::Portable::Parameter::kTypeID || !object)
    return false;
  const auto *parameter = static_cast<Core::Portable::Parameter *>(object);
  return std::strcmp(parameter->getName(), "mute") == 0;
}
bool MuteGroupBase::Filter::shouldSave(int typeId, const char *name,
                                       void *object) const {
  if (!Filter::shouldLoad(typeId, name, object))
    return false;
  if (typeId == Core::Portable::Component::kTypeID)
    return true;
  return static_cast<Core::Portable::Parameter *>(object)->getValue() != 0.f;
}
} // namespace Presonus
