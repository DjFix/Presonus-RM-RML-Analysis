#include "presonus/panel/GeqUIComponent.hpp"
#include <stdexcept>
namespace Presonus::Panel {
Mixer::ChannelComponent *GeqUIComponent::getChannelAssignedToCurrentGeq() {
  if (currentGeq < 0)
    return nullptr;
  if (!channelSelection)
    throw std::logic_error("Geq channel selection input is not bound");
  if (currentGeq <= 1)
    return channelSelection->main.isEmpty() ? nullptr
                                            : channelSelection->main.first();
  if (currentGeq >= channelSelection->geqCount ||
      channelSelection->aux.isEmpty())
    return nullptr;
  return channelSelection->aux.at(currentGeq - 2);
}
} // namespace Presonus::Panel
