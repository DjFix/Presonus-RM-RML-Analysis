#pragma once
#include "core/public/corelinkedlist.h"
#include "core/system/corethread.h"
namespace presonus::uc {
// Independent construction tag; no original exported queue constructor exists.
struct MessageQueuePortTag {};
struct MessageQueuePortAccess;
} // namespace presonus::uc
namespace Presonus::UC {
class MessageAttributes;
// Independent storage composition. Original ARM lock/list layout and original
// inheritance are unresolved. Core is the actual pinned upstream
// implementation.
class MessageQueue {
public:
  explicit MessageQueue(presonus::uc::MessageQueuePortTag);
  ~MessageQueue();
  MessageQueue(const MessageQueue &) = delete;
  MessageQueue &operator=(const MessageQueue &) = delete;
  MessageQueue(MessageQueue &&) = delete;
  MessageQueue &operator=(MessageQueue &&) = delete;
  // Original ordinary return declarations remain unresolved. These are portable
  // source choices; a null item stops removeAll even if later nodes remain.
  void add(MessageAttributes *);
  MessageAttributes *retrieve();
  void removeAll();

private:
  friend struct presonus::uc::MessageQueuePortAccess;
  Core::Threads::Lock lock_;
  Core::LinkedList<MessageAttributes *> messages_;
};
} // namespace Presonus::UC
namespace presonus::uc {
struct MessageQueuePortAccess {
  static Core::Threads::Lock &lock(Presonus::UC::MessageQueue &queue) {
    return queue.lock_;
  }
  static const auto &messages(const Presonus::UC::MessageQueue &queue) {
    return queue.messages_;
  }
};
} // namespace presonus::uc
