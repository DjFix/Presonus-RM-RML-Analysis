#include "presonus/FileMuteGroup.hpp"
#include "core/portable/corepersistence.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include <stdexcept>

namespace Presonus {
FileMuteGroup::FileMuteGroup(Core::Portable::FileName filename,
                             Core::Portable::Parameter *parameter,
                             Mixer::MixerComponentBase &mixer)
    : MuteGroupBase(mixer), Core::Portable::Component(""), filename_(filename),
      parameter_(parameter) {
  parameter_->addObserver(this);
}
FileMuteGroup::~FileMuteGroup() {
  if (parameter_)
    parameter_->removeObserver(this);
}
void FileMuteGroup::paramChanged(Core::Portable::Parameter *parameter,
                                 int message) {
  if (!parameter_)
    throw std::logic_error("unbound compatibility FileMuteGroup");
  if (message == 3 && reactivate_ && parameter->getValue() == 0.f) {
    parameter->setValue(1.f, false);
    reactivate_ = false;
  }
}
void FileMuteGroup::activate() {
  if (!mixer || !mixer->saveServices.parameters)
    throw std::logic_error("mute parameter tree is not bound");
  Core::Portable::DefaultAllocatedAttributes attributes;
  if (!Core::Portable::ArchiveUtils::loadFromFile(
          attributes, filename_, Core::Portable::Archiver::kJSON, nullptr, 0,
          false))
    return;
  Filter filter;
  Core::Portable::InputStorage storage(attributes, &filter);
  if (mixer->saveServices.parameters->load(storage))
    cacheMutes(attributes);
}
void FileMuteGroup::cacheMutes(const Core::Portable::Attributes &attributes) {
  if (!mixerData)
    throw std::logic_error("mute mixer data is not bound");
  state.members.empty();
  for (int i = 0; i < mixerData->channels.count(); ++i) {
    const auto &channel = mixerData->channels[i];
    const auto *parent = attributes.getAttributes(channel.parentName);
    const auto *child = parent ? parent->getAttributes(channel.name) : nullptr;
    const auto *value =
        child ? child->lookup(channel.mute->getName()) : nullptr;
    if (value && (value->getType() == Core::Portable::AttributeValue::kInt ||
                  value->getType() == Core::Portable::AttributeValue::kFloat)) {
      // Native converts floating attribute payloads to signed int64 before the
      // positivity check. Bounded port domain: finite representable int64.
      const auto positive =
          value->getType() == Core::Portable::AttributeValue::kInt
              ? value->getInt() > 0
              : static_cast<Core::int64>(value->getFloat()) > 0;
      if (positive)
        state.members.add(channel.mute);
    }
  }
  updateStatus();
}

bool FileMuteGroup::findAttribute(const Core::Portable::Attributes *attributes,
                                  const char *path, const char *attribute) {
  while (attributes) {
    if (!attributes->lookup(path))
      return attributes->lookup(attribute) != nullptr;
    attributes = attributes->getAttributes(path);
  }
  return false;
}
} // namespace Presonus
