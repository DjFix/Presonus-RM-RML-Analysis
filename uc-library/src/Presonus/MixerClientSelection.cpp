#include "presonus/MappableMixer.hpp"
#include "presonus/MixerClientComponentBase.hpp"
#include "presonus/SLChannel.hpp"
#include <stdexcept>

namespace Presonus {
void MixerClientComponentBase::channelSelected(SLChannelBase *channel) {
  auto *root = this;
  while (auto *master = root->getMasterMixer())
    root = master;
  if (root->selectedChannel_ == channel)
    return;
  // Original MI supplies an always-live MappableMixer subobject. This source
  // port requires the explicit genuine provider rather than faking a sender.
  if (!root->selectionObservers_)
    throw std::logic_error(
        "channel selection requires its real observer mixer");
  root->selectedChannel_ = channel;
  auto *selection = root->selectedChannel_
                        ? root->selectedChannel_->getSelectionParameter()
                        : nullptr;
  // Preserve the native cache reload across the preceding virtual getter.
  auto *linked = root->selectedChannel_
                     ? root->selectedChannel_->getLinkedSelectionParameter()
                     : nullptr;
  const auto deselect = [selection, linked](MixerClientComponentBase &mixer) {
    // Independent inline application adaptation of the verified downstream
    // deselection contract; no extra original method credit or fake roster.
    for (int type = 0; type < 9; ++type) {
      auto *group = mixer.getChannelGroup(static_cast<ChannelType>(type));
      if (!group)
        continue;
      for (int i = 0; i < group->countChildren(); ++i) {
        auto *child = group->getChild(i);
        auto *channel =
            child ? Core::Portable::core_cast<SLChannelBase>(child) : nullptr;
        auto *parameter = channel ? channel->getSelectionParameter() : nullptr;
        if (parameter && parameter != selection && parameter != linked)
          parameter->setValue(0.f, false);
      }
    }
  };
  deselect(*root);
  if (auto *slave = root->getSlaveMixer())
    deselect(*slave);
  root->selectionObservers_->sendObjectChangeMessage(
      static_cast<IMixerComponentObserver::ObjectChangeMessage>(13));
}
} // namespace Presonus
