#include "presonus/uc/event_queue.hpp"
#include <cstring>
#include <type_traits>

namespace presonus::uc {
// Independent RAII contract. This invokes supplied synchronization callbacks,
// without defining or replacing any Core lock class/body/symbol.
class QueueGuard {
public:
  explicit QueueGuard(EventQueueState &state) : state_(state) {
    state_.lock(state_.context);
  }
  ~QueueGuard() { state_.unlock(state_.context); }
  QueueGuard(const QueueGuard &) = delete;
  QueueGuard &operator=(const QueueGuard &) = delete;

private:
  EventQueueState &state_;
};
template <class T> constexpr QueueValueKind kind() {
  if constexpr (std::is_same_v<T, Presonus::UC::ParamValueEvent>)
    return QueueValueKind::Value;
  else if constexpr (std::is_same_v<T, Presonus::UC::ParamIncrementEvent>)
    return QueueValueKind::Increment;
  else if constexpr (std::is_same_v<T, Presonus::UC::ParamColorEvent>)
    return QueueValueKind::Color;
  else if constexpr (std::is_same_v<T, Presonus::UC::ParamStringEvent>)
    return QueueValueKind::String;
  else if constexpr (std::is_same_v<T, Presonus::UC::ParamStringListEvent>)
    return QueueValueKind::StringList;
  else if constexpr (std::is_same_v<T, Presonus::UC::ParamRangeEvent>)
    return QueueValueKind::Range;
  else if constexpr (std::is_same_v<T, Presonus::UC::FileDataRateEvent>)
    return QueueValueKind::FileRate;
  else
    return QueueValueKind::TimeCode;
}
} // namespace presonus::uc
namespace Presonus::UC {
template <class T> bool EventQueue::update(const Event &event) {
  presonus::uc::QueueGuard guard(state_);
  auto *node = state_.head;
  auto *ownedItem =
      state_.owned ? state_.owned->items.value().getFirst() : nullptr;
  while (state_.owned ? ownedItem != nullptr : node != nullptr) {
    auto *item = state_.owned ? ownedItem : node->item;
    // Advance before inspecting/calling payload views, as in the original.
    if (state_.owned)
      ownedItem = item->getNext();
    else
      node = node->next;
    if (item->getData().type != event.type)
      continue;
    Event &queued = item->getData();
    if (queued.routeA != event.routeA || queued.routeB != event.routeB)
      continue;
    T &destination = *static_cast<T *>(
        state_.value(state_.context, queued, presonus::uc::kind<T>()));
    const T &source = *static_cast<const T *>(
        state_.value(state_.context, event, presonus::uc::kind<T>()));
    if constexpr (std::is_same_v<T, FileDataRateEvent>) {
      if (destination.idBits != source.idBits)
        continue;
      destination.wordBits[0] = source.wordBits[0];
    } else if constexpr (std::is_same_v<T, TimeCodeEvent>) {
      if (destination.keyBits != source.keyBits)
        continue;
      destination.records = source.records;
      destination.recordCount = source.recordCount;
    } else {
      if (std::strcmp(destination.path.data(), source.path.data()))
        continue;
      if constexpr (std::is_same_v<T, ParamValueEvent>) {
        destination.valueBits = source.valueBits;
        destination.index = source.index;
      } else if constexpr (std::is_same_v<T, ParamIncrementEvent>) {
        destination.incrementBits = static_cast<unsigned short>(
            destination.incrementBits + source.incrementBits);
      } else if constexpr (std::is_same_v<T, ParamColorEvent>) {
        destination.colorBits = source.colorBits;
      } else if constexpr (std::is_same_v<T, ParamStringEvent>) {
        destination.index = source.index;
        std::strcpy(destination.text.data(), source.text.data());
      } else if constexpr (std::is_same_v<T, ParamStringListEvent>) {
        destination.index = source.index;
        destination.listFieldBits = source.listFieldBits;
        std::strcpy(destination.text.data(), source.text.data());
      } else if constexpr (std::is_same_v<T, ParamRangeEvent>) {
        // The original transiently stores sourceword1 into destinationword3,
        // then overwrites word3. Destinationword1 is left unchanged.
        destination.wordBits[3] = source.wordBits[1];
        destination.wordBits[3] = source.wordBits[3];
        destination.wordBits[0] = source.wordBits[0];
        destination.wordBits[2] = source.wordBits[2];
        destination.wordBits[4] = source.wordBits[4];
        destination.index = source.index;
        std::strcpy(destination.labels[0].data(), source.labels[0].data());
        std::strcpy(destination.labels[1].data(), source.labels[1].data());
      }
    }
    return true;
  }
  return false;
}
bool EventQueue::updateEvent(const Event &event) {
  switch (event.type) {
  case 20566:
    return update<ParamValueEvent>(event);
  case 20553:
    return update<ParamIncrementEvent>(event);
  case 20547:
    return update<ParamColorEvent>(event);
  case 20563:
    return update<ParamStringEvent>(event);
  case 20556:
    return update<ParamStringListEvent>(event);
  case 20562:
    return update<ParamRangeEvent>(event);
  case 18003:
    return update<FileDataRateEvent>(event);
  case 21571:
    return update<TimeCodeEvent>(event);
  default:
    return false;
  }
}
template bool EventQueue::update<ParamValueEvent>(const Event &);
template bool EventQueue::update<ParamIncrementEvent>(const Event &);
template bool EventQueue::update<ParamColorEvent>(const Event &);
template bool EventQueue::update<ParamStringEvent>(const Event &);
template bool EventQueue::update<ParamStringListEvent>(const Event &);
template bool EventQueue::update<ParamRangeEvent>(const Event &);
template bool EventQueue::update<FileDataRateEvent>(const Event &);
template bool EventQueue::update<TimeCodeEvent>(const Event &);
} // namespace Presonus::UC
