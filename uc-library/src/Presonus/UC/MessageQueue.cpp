#include "presonus/uc/message_attributes.hpp"
#include "presonus/uc/message_queue.hpp"
namespace Presonus::UC {
MessageQueue::MessageQueue(presonus::uc::MessageQueuePortTag) {}
MessageQueue::~MessageQueue() { removeAll(); }
void MessageQueue::add(MessageAttributes *message) {
  Core::Threads::ScopedLock guard(lock_);
  messages_.append(message);
}
MessageAttributes *MessageQueue::retrieve() {
  Core::Threads::ScopedLock guard(lock_);
  return messages_.removeFirst();
}
void MessageQueue::removeAll() {
  while (auto *message = retrieve())
    delete message;
}
} // namespace Presonus::UC
