#include "presonus/trial08/MixerComponentBase.hpp"
#include <cstring>
#include <stdexcept>
namespace Presonus::Mixer {
// CCL implements the compacting removal and error-slot reset. The ordinary
// void return is a portable source contract, not an original declaration claim.
void MixerComponentBase::removeDelegate(Delegate &delegate) {
  delegates.remove(&delegate);
}
ChannelComponent *
MixerComponentBase::getLinkableChannelPair(ChannelComponent *channel) const {
  if (!channelIdentity)
    throw std::logic_error("channel identity query binding required");
  const auto identity = channelIdentity(channel);
  const Core::Vector<ChannelComponent *> *channels;
  if (identity.first == 0)
    channels = &inputChannels;
  else if (identity.first == 4)
    channels = &mixChannels;
  else
    return nullptr;
  if (channels->isEmpty())
    return nullptr;
  const auto bits = static_cast<std::uint32_t>(identity.second) ^ 1u;
  std::int32_t sibling;
  std::memcpy(&sibling, &bits, sizeof(sibling));
  return channels->at(sibling);
}
} // namespace Presonus::Mixer
