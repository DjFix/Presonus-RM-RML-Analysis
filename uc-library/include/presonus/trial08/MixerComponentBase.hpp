#pragma once
#include "core/public/corevector.h"
#include <cstdint>
#include <functional>
#include <utility>
namespace Presonus::Mixer {
class ChannelComponent;
// Portable state model. Fields and return declarations are source-port choices,
// not recovered ARM layout or independently established original declarations.
class MixerComponentBase {
public:
  class Delegate;
  // Independent portable state; no original layout or ownership claim.
  Core::Vector<Delegate *> delegates;
  void removeDelegate(Delegate &delegate);
  // Required independent identity query, not recovered Channel fields.
  std::function<std::pair<std::int32_t, std::int32_t>(ChannelComponent *)>
      channelIdentity;
  Core::Vector<ChannelComponent *> inputChannels, mixChannels;
  ChannelComponent *getLinkableChannelPair(ChannelComponent *) const;
  // Independent source-port contract moved from the competing definition;
  // original Filter layout remains unresolved.
  struct Filter {
    int selector{};
  };
  std::uint32_t selectedChannel = 0;
  std::uint32_t clientCount = 0;
  std::uint32_t hardwareMicLineInputs = 0;
  bool tryingToQuit = false;
  std::uint32_t getSelectedChannel() const;
  std::uint32_t numClients() const;
  std::uint32_t numHWMicLineIn() const;
  const char *getCompanyName() const;
  std::uint32_t getSpectrumSendSlot() const;
  void setTryingToQuit();
};
} // namespace Presonus::Mixer
