#include "presonus/MappableMixer.hpp"
#include "presonus/MixerClientComponentBase.hpp"
#include "presonus/SLChannel.hpp"
#include "presonus/uc/ClientRootComponent.hpp"
#include "presonus/uc/client_implementation.hpp"
#include <stdexcept>

namespace Presonus {
SLChannelBase::ParamLinker::ParamLinker(MixerClientComponentBase &mixer,
                                        SLChannelBase &source,
                                        SLChannelBase &neighbour)
    : mixer_(mixer), source_(source), neighbour_(neighbour),
      link_(source.getLinkParameter()) {
  Core::Vector<Core::Portable::Parameter *> parameters;
  source.getSlowLinkParams(parameters);
  for (int i = 0; i < parameters.count(); ++i) {
    auto *parameter = parameters.at(i);
    parameter->addObserver(this);
    observed_.add(parameter);
  }
}
SLChannelBase::ParamLinker::~ParamLinker() {
  for (int i = 0; i < observed_.count(); ++i)
    observed_.at(i)->removeObserver(this);
}
bool SLChannelBase::ParamLinker::isLinked() const {
  return link_ && link_->getValue() > 0.f;
}
void SLChannelBase::ParamLinker::paramChanged(
    Core::Portable::Parameter *parameter, int msg) {
  if (msg != Core::Portable::Parameter::kChanged || !isLinked() ||
      !parameter->isEditing())
    return;
  if (auto *peer = neighbour_.getParameterByTag(parameter->getTag())) {
    peer->setValue(parameter->getValue(), false);
    if (auto *root = source_.getRoot())
      if (auto *client = root->sourcePortParameterClient())
        client->setLastParamChange(peer);
  }
}
Core::Portable::Parameter *SLChannel::getLinkParameter() const {
  return getParameterByTag(21);
}
Core::Portable::Parameter *SLChannel::getLinkMasterParameter() const {
  return getParameterByTag(22);
}
void SLChannel::getSlowLinkParams(
    Core::Vector<Core::Portable::Parameter *> &parameters) const {
  static constexpr int tags[] = {17,  20,  18,  224, 225, 226, 227, 228,
                                 229, 230, 231, 232, 233, 234, 235, 236,
                                 237, 238, 239, 300, 301, 302, 303};
  for (int tag : tags)
    if (auto *parameter = getParameterByTag(tag))
      parameters.add(parameter);
}
void SLChannelBase::paramChanged(Core::Portable::Parameter *parameter,
                                 int msg) {
  using Core::Portable::Parameter;
  UC::ClientComponent::paramChanged(parameter, msg);
  if (msg == Parameter::kEdit) {
    if (parameter == getSelectionParameter()) {
      parameter->setValue(1.f, false);
      updateLinkedSelection(true);
    } else if (parameter == getLinkParameter())
      updateLinkedSelection(true);
    return;
  }
  if (msg != Parameter::kChanged)
    return;
  if (parameter == getLinkParameter() ||
      parameter == getLinkMasterParameter()) {
    if (observerMixer_)
      observerMixer_->sendObjectChangeMessage(
          static_cast<IMixerComponentObserver::ObjectChangeMessage>(9));
    if (parameter == getLinkParameter()) {
      auto *selection = getSelectionParameter();
      if (selection && selection->getValue() > 0.f)
        updateLinkedSelection(false);
      return;
    }
  }
  if (parameter == getColorParameter()) {
    updateColorIndex();
    auto *observer = mixer_ && mixer_->getMasterMixer() ? masterObserverMixer_
                                                        : observerMixer_;
    if (observer)
      observer->sendObjectChangeMessage(
          static_cast<IMixerComponentObserver::ObjectChangeMessage>(11));
  } else if (parameter->getTag() == 15002)
    updateColorFromIndex();
}
void SLChannel::paramChanged(Core::Portable::Parameter *parameter, int msg) {
  using Core::Portable::Parameter;
  SLChannelBase::paramChanged(parameter, msg);
  if (msg == Parameter::kEdit) {
    const auto tag = static_cast<unsigned>(parameter->getTag());
    if (tag - 256u > 15u)
      return;
    auto *mixer = sourcePortMutableMixer();
    auto *observer = mixer && mixer->getMasterMixer()
                         ? sourcePortMasterObserverMixer()
                         : sourcePortObserverMixer();
    if (observer)
      observer->sendObjectChangeMessage(
          static_cast<IMixerComponentObserver::ObjectChangeMessage>(10));
  } else if (msg == Parameter::kChanged && parameter->getTag() == 411) {
    if (auto *observer = sourcePortObserverMixer())
      observer->sendObjectChangeMessage(
          static_cast<IMixerComponentObserver::ObjectChangeMessage>(10));
  }
}
void SLChannelBase::updateLinkedSelection(bool notifyMixer) {
  const bool linked = linker_ && linker_->isLinked();
  if (auto *parameter = getLinkedSelectionParameter())
    parameter->setValue(linked ? 1.f : 0.f, false);
  if (notifyMixer) {
    if (!mixer_)
      throw std::logic_error("initialized channel requires its real mixer");
    mixer_->channelSelected(this);
  }
}
} // namespace Presonus
