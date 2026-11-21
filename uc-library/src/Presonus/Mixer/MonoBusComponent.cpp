#include "presonus/mixer/MonoBusComponent.hpp"
#include "core/public/corestringbuffer.h"

namespace Presonus::Mixer {

void MonoBusComponent::paramChanged(Core::Portable::Parameter *parameter,
                                    int message) {
  if (!bindings_) {
    ChannelComponent::paramChanged(parameter, message);
    return;
  }
  if (!parameter)
    return;

  auto &bindings = *bindings_;
  bindings.sendOutput.paramChanged(parameter, message);
  const int tag = parameter->getTag();

  if (message == Core::Portable::Parameter::kChanged &&
      (tag == 410 || tag == 411)) {
    bindings.ownSendState.sendChanged = 1;
    bindings.ownSendState.output.updatePending = true;
    for (auto *group : bindings.affectedSendGroups) {
      if (!group)
        continue;
      for (int index = 0; index < group->count(); ++index) {
        if (auto *send = group->at(index)) {
          send->childChanged = 1;
          send->output.updatePending = true;
        }
      }
    }
    return;
  }

  if (message != Core::Portable::Parameter::kEdit)
    return;

  if (tag == 21) {
    auto *mode = getParameterByTag(411);
    if (!mode || !(mode->getValue() > 0.f) || !(parameter->getValue() > 0.f))
      return;
    const int firstTag =
        256 + (static_cast<unsigned>(bindings.index) & 0xfffeu);
    for (int index = 0; index < bindings.sendChannels.count(); ++index) {
      if (auto *channel = bindings.sendChannels.at(index)) {
        auto *first = channel->getParameterByTag(firstTag);
        auto *second = channel->getParameterByTag(firstTag + 1);
        if (first && second &&
            (first->getValue() > 0.f || second->getValue() > 0.f)) {
          first->setValue(1.f, true);
          second->setValue(1.f, true);
        }
      }
    }
    return;
  }

  if (tag != 411)
    return;

  const bool subgroup = parameter->getValue() > 0.f;
  if (bindings.updateChannelNames) {
    for (int index = 0; index < bindings.sendChannels.count(); ++index) {
      if (auto *channel = bindings.sendChannels.at(index))
        if (auto *assignment = channel->getParameterByTag(bindings.index + 256))
          assignment->setValue(subgroup ? 0.f : 1.f, true);
    }
    Core::CString32 displayName;
    displayName.appendFormat("%s %d", subgroup ? "Sub" : bindings.sourceName,
                             bindings.index + 1);
    for (int tag : {2, 1})
      if (auto *name = getParameterByTag(tag))
        name->fromString(displayName, true);

    if (auto *name = getParameterByTag(0)) {
      Core::CString32 shortName;
      shortName.appendFormat("%c%d", subgroup ? 'S' : 'A', bindings.index + 1);
      name->fromString(shortName, true);
    }
  }

  if (auto *alias = bindings.rangeAlias) {
    alias->setMin(subgroup ? 2.f : 0.f);
    if (bindings.updateChannelNames)
      alias->resetValue(true);
  }
}

} // namespace Presonus::Mixer
