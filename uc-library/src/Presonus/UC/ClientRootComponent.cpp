#include "presonus/uc/ClientRootComponent.hpp"
#include "core/portable/coreattributes.h"
#include "core/system/coretime.h"

namespace Presonus::UC {

void *ClientRootComponent::castTo(int typeId) {
  if (typeId == kTypeID)
    return this;
  return ClientComponent::castTo(typeId);
}

ClientRootComponent *ClientRootComponent::getRoot() { return this; }

Core::abs_time ClientRootComponent::getSystemTime() const {
  // Match the native signed quotient at millisecond boundaries.
  constexpr Core::abs_time nanosecondsPerMillisecond = 1000000;
  return Core::SystemClock::getTime() / nanosecondsPerMillisecond;
}

void ClientRootComponent::receiveEvent(const BinaryEvent &) {}
void ClientRootComponent::receiveEvent(const DebugEvent &) {}
void ClientRootComponent::receiveEvent(const TimeCodeEvent &) {}
void ClientRootComponent::updateLevels(const MeterEvent &) {}
void ClientRootComponent::subscriptionReply(const MessageAttributes *) {}

bool ClientRootComponent::collectAll(Core::Portable::Attributes &attributes,
                                     ClientComponent &component) const {
  using Core::Portable::ColorParam;
  using Core::Portable::ParamInfo;
  auto *values = attributes.addAttributes("values");
  for (int i = 0; i < component.countParameters(); ++i) {
    auto *parameter = component.getParameterAt(i);
    if (!parameter->isPublic())
      continue;
    const auto *name = parameter->getName();
    switch (parameter->getType()) {
    case ParamInfo::kColor:
      if (const auto *color = ColorParam::cast(parameter))
        values->add(name, static_cast<Core::int64>(color->getColor()));
      break;
    case ParamInfo::kString: {
      Core::CString256 text;
      parameter->toString(text.getBuffer(), 256);
      values->add(name, text.str());
      break;
    }
    default:
      values->add(name, static_cast<double>(parameter->getValue()));
      break;
    }
  }
  const bool hasValues = values->countAttributes() != 0;
  if (!hasValues)
    attributes.remove("values");

  bool hasChildren = false;
  if (component.countChildren() > 0) {
    constexpr int clientComponentType = 0x436c436f;
    auto *children = attributes.addAttributes("children");
    for (int i = 0; i < component.countChildren(); ++i) {
      auto *child = component.getChild(i);
      auto *client = child ? static_cast<ClientComponent *>(
                                 child->castTo(clientComponentType))
                           : nullptr;
      if (!client)
        continue;
      auto *childAttributes = children->addAttributes(client->getName());
      if (collectAll(*childAttributes, *client))
        hasChildren = true;
      else
        children->remove(client->getName());
    }
    if (!hasChildren)
      attributes.remove("children");
  }
  return hasValues || hasChildren;
}

} // namespace Presonus::UC
