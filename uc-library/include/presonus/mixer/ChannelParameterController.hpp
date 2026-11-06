#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/mixer/ChannelComponent.hpp"
namespace Presonus::Mixer {
// Explicit source-port adapter, not an original ChannelComponent layout.
// CCL owns registered parameters/children. The referenced channel must outlive
// this controller. The stable signed index is supplied by the owning channel
// tree.
class ChannelParameterController : public Core::Portable::Component {
public:
  DECLARE_CORE_CLASS('ChPC', ChannelParameterController,
                     Core::Portable::Component)
  ChannelParameterController(ChannelComponent &channel, int index);
  ChannelComponent &channel() const { return channel_; }
  int channelIndex() const { return index_; }

private:
  ChannelComponent &channel_;
  const int index_;
};
} // namespace Presonus::Mixer
