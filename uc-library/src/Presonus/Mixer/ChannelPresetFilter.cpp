#include "presonus/mixer/ChannelPresetFilter.hpp"
#include "core/portable/corecomponent.h"
#include <cstring>
namespace Presonus::Mixer {
bool ChannelPresetFilter::shouldLoad(int typeId, const char *name,
                                     void *) const {
  // Original literal is Comp (0x436f6d70), despite the earlier task prose.
  if (typeId != Core::Portable::Component::kTypeID)
    return true;
  if (!name)
    name = "";
  if ((!std::strcmp(name, "eq") || !std::strcmp(name, "filter")) && equalizer_)
    return equalizer_->getValue() > 0.f;
  if (!std::strcmp(name, "gate") && gate_)
    return gate_->getValue() > 0.f;
  if (!std::strcmp(name, "comp") && compressor_)
    return compressor_->getValue() > 0.f;
  return true;
}
bool ChannelPresetFilter::shouldSave(int typeId, const char *,
                                     void *object) const {
  if (object == target_)
    return true;
  if (typeId == Core::Portable::Component::kTypeID)
    return true;
  if (typeId != Core::Portable::Parameter::kTypeID || !object)
    return false;
  auto *parameter = static_cast<Core::Portable::Parameter *>(object);
  auto *component = Core::Portable::core_cast<Core::Portable::Component>(
      parameter->getController());
  if (!component)
    return false;
  const char *name = component->getName();
  return !std::strcmp(name, "comp") || !std::strcmp(name, "limit") ||
         !std::strcmp(name, "eq") || !std::strcmp(name, "filter") ||
         !std::strcmp(name, "gate");
}
} // namespace Presonus::Mixer
