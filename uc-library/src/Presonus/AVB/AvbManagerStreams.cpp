#include "presonus/avb/protocol.hpp"
#include "presonus/avb/receive_services.hpp"
#include <stdexcept>

namespace Presonus::AVB {
void AvbManagerBase::removeListener(AvbListener *listener) {
  if (!receiveContext_)
    throw std::logic_error("AVB requires receive context");
  if (receiveContext_->listeners.remove(listener))
    delete listener;
}
void AvbManagerBase::removeTalker(AvbTalker *talker) {
  if (!receiveContext_)
    throw std::logic_error("AVB requires receive context");
  if (receiveContext_->talkers.remove(talker))
    delete talker;
}
void AvbManagerBase::removeAllListeners() {
  if (!receiveContext_)
    throw std::logic_error("AVB requires receive context");
  for (auto *listener : receiveContext_->listeners)
    delete listener;
  receiveContext_->listeners.removeAll();
}
AvbListener *AvbManagerBase::addListener(unsigned long long identifier,
                                         unsigned short suffix,
                                         unsigned char channels) {
  const auto capacity = streamCapacity();
  if (!receiveContext_)
    throw std::logic_error("AVB requires receive context");
  // Original comparison is strictly greater, allowing capacity+1 streams and
  // identifier==capacity when all lower IDs are occupied. Preserve that edge.
  if (receiveContext_->listeners.count() > capacity)
    return nullptr;
  unsigned char index = 0;
  while (index < capacity && findListener(index))
    ++index;
  resizeListener(index, channels);
  auto *listener = new AvbListener(index, identifier, suffix, channels);
  receiveContext_->listeners.append(listener);
  subscribe(index, listener->inspectState().streamKey);
  return listener;
}
AvbTalker *AvbManagerBase::addTalker(unsigned char channels) {
  const auto capacity = streamCapacity();
  if (!receiveContext_)
    throw std::logic_error("AVB requires receive context");
  if (receiveContext_->talkers.count() > capacity)
    return nullptr;
  unsigned char index = 0;
  while (index < capacity && findTalker(index))
    ++index;
  resizeTalker(index, channels);
  auto *talker = new AvbTalker(index, channels);
  receiveContext_->talkers.append(talker);
  publish(index, true);
  return talker;
}
} // namespace Presonus::AVB
