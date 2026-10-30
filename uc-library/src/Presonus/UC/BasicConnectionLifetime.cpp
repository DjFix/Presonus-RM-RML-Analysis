#include "core/public/corehashmap.h"
#include "presonus/uc/basic_connection_runtime.hpp"
#include <cassert>
#include <stdexcept>

namespace presonus::uc {
namespace {
const BasicConnectionProviders *currentProviders = nullptr;
unsigned liveOwnedConnections = 0;
const BasicConnectionProviders &requireProviders() {
  if (!currentProviders)
    throw std::logic_error("real BasicConnection source providers required");
  return *currentProviders;
}
struct LifetimeCount {
  LifetimeCount() { ++liveOwnedConnections; }
  ~LifetimeCount() { --liveOwnedConnections; }
};
template <class T> void *typed(Presonus::UC::EventItem &item) {
  auto *value = dynamic_cast<TypedEventItem<T> *>(&item);
  if (!value)
    throw std::invalid_argument("live matching typed queue item required");
  return &value->value;
}
} // namespace

struct BasicConnectionTypedValues::State {
  struct Entry {
    void *value = nullptr;
    QueueValueKind kind = QueueValueKind::Value;
    bool operator==(const Entry &other) const {
      return value == other.value && kind == other.kind;
    }
  };
  static int hash(const Presonus::UC::Event *const &header, int size) {
    return int((reinterpret_cast<std::uintptr_t>(header) >> 3) %
               std::uintptr_t(size));
  }
  Core::HashMap<const Presonus::UC::Event *, Entry> entries{32, hash};
};
BasicConnectionTypedValues::BasicConnectionTypedValues()
    : state_(std::make_shared<State>()) {}
BasicConnectionTypedValues::~BasicConnectionTypedValues() = default;
BasicConnectionTypedValues::Binding::Binding(std::shared_ptr<State> state,
                                             const Presonus::UC::Event *header)
    : state_(std::move(state)), header_(header) {}
BasicConnectionTypedValues::Binding::~Binding() {
  if (state_)
    state_->entries.remove(header_);
}
void BasicConnectionTypedValues::bindValue(Presonus::UC::Event &header,
                                           void *value, QueueValueKind kind) {
  State::Entry old;
  if (!value || state_->entries.get(old, &header))
    throw std::invalid_argument("unique live external typed value required");
  state_->entries.add(&header, {value, kind});
}
#define DEFINE_BIND(Type, Kind)                                                \
  BasicConnectionTypedValues::Binding BasicConnectionTypedValues::bind(        \
      Presonus::UC::Type &value) {                                             \
    bindValue(value.header, &value, QueueValueKind::Kind);                     \
    return Binding(state_, &value.header);                                     \
  }
DEFINE_BIND(ParamValueEvent, Value)
DEFINE_BIND(ParamIncrementEvent, Increment)
DEFINE_BIND(ParamColorEvent, Color)
DEFINE_BIND(ParamStringEvent, String)
DEFINE_BIND(ParamStringListEvent, StringList)
DEFINE_BIND(ParamRangeEvent, Range)
DEFINE_BIND(FileDataRateEvent, FileRate)
DEFINE_BIND(TimeCodeEvent, TimeCode)
#undef DEFINE_BIND

std::optional<BasicConnectionTypedValues::Binding>
BasicConnectionTypedValues::bindIncoming(Presonus::UC::EventItem &item,
                                         unsigned type) {
#define BIND_ITEM(Type, Id)                                                    \
  case Id: {                                                                   \
    auto *typedItem =                                                          \
        dynamic_cast<TypedEventItem<Presonus::UC::Type> *>(&item);             \
    if (!typedItem)                                                            \
      throw std::invalid_argument("matching incoming typed item required");    \
    return bind(typedItem->value);                                             \
  }
  switch (type) {
    BIND_ITEM(ParamValueEvent, 20566)
    BIND_ITEM(ParamIncrementEvent, 20553)
    BIND_ITEM(ParamColorEvent, 20547)
    BIND_ITEM(ParamStringEvent, 20563)
    BIND_ITEM(ParamStringListEvent, 20556)
    BIND_ITEM(ParamRangeEvent, 20562)
    BIND_ITEM(FileDataRateEvent, 18003)
    BIND_ITEM(TimeCodeEvent, 21571)
  default:
    return std::nullopt;
  }
#undef BIND_ITEM
}
void *BasicConnectionTypedValues::resolve(
    const Presonus::UC::Event &header, QueueValueKind kind,
    const Core::IntrusiveLinkedList<Presonus::UC::EventItem> &items) const {
  for (auto *item = items.getFirst(); item; item = item->getNext()) {
    if (&item->getData() != &header)
      continue;
    switch (kind) {
    case QueueValueKind::Value:
      return typed<Presonus::UC::ParamValueEvent>(*item);
    case QueueValueKind::Increment:
      return typed<Presonus::UC::ParamIncrementEvent>(*item);
    case QueueValueKind::Color:
      return typed<Presonus::UC::ParamColorEvent>(*item);
    case QueueValueKind::String:
      return typed<Presonus::UC::ParamStringEvent>(*item);
    case QueueValueKind::StringList:
      return typed<Presonus::UC::ParamStringListEvent>(*item);
    case QueueValueKind::Range:
      return typed<Presonus::UC::ParamRangeEvent>(*item);
    case QueueValueKind::FileRate:
      return typed<Presonus::UC::FileDataRateEvent>(*item);
    case QueueValueKind::TimeCode:
      return typed<Presonus::UC::TimeCodeEvent>(*item);
    }
  }
  State::Entry entry;
  if (!state_->entries.get(entry, &header) || entry.kind != kind ||
      !entry.value)
    throw std::invalid_argument("live external typed value binding required");
  return entry.value;
}
BasicConnectionProviderScope::BasicConnectionProviderScope(
    Presonus::UC::EventFactory &factory, BasicConnectionTypedValues &values)
    : providers_{factory, values} {
  if (currentProviders)
    throw std::logic_error("BasicConnection provider scope already active");
  currentProviders = &providers_;
}
BasicConnectionProviderScope::~BasicConnectionProviderScope() {
  // Explicit serialized lifetime contract; never hide invalid shutdown.
  if (currentProviders != &providers_ || liveOwnedConnections)
    std::terminate();
  currentProviders = nullptr;
}
} // namespace presonus::uc

namespace Presonus::UC {
struct BasicConnection::SourceOwned {
  presonus::uc::BasicConnectionProviders providers;
  presonus::uc::LifetimeCount lifetime;
  presonus::uc::BasicQueueStorage storage;
  EventQueue queue;
  presonus::uc::BasicConnectionState bridge;
  explicit SourceOwned(const presonus::uc::BasicConnectionProviders &source)
      : providers(source),
        storage(presonus::uc::makeBasicQueueStorage(this, resolve)),
        queue(*storage), bridge{&queue, &providers.factory, &storage->view,
                                storage.get(), append} {}
  static void *resolve(void *context, const Event &event,
                       presonus::uc::QueueValueKind kind) {
    auto &self = *static_cast<SourceOwned *>(context);
    return self.providers.values.resolve(event, kind,
                                         self.storage->items.value());
  }
  static void append(void *context, EventItem *item) {
    static_cast<presonus::uc::OwnedEventQueueState *>(context)->append(item);
  }
};
BasicConnection::BasicConnection(presonus::uc::BasicConnectionState &state)
    : state_(state) {}
BasicConnection::BasicConnection(int type)
    : BasicConnection(type, presonus::uc::requireProviders()) {}
BasicConnection::BasicConnection(
    int type, const presonus::uc::BasicConnectionProviders &providers)
    : connectionType_(type),
      activity_(&presonus::uc::sourceActivitySingleton()),
      owned_(std::make_unique<SourceOwned>(providers)), state_(owned_->bridge) {
}
BasicConnection::~BasicConnection() = default;
} // namespace Presonus::UC

namespace presonus::uc {
int BasicConnectionSourceAccess::connectionType(
    const Presonus::UC::BasicConnection &connection) {
  return connection.connectionType_;
}
Presonus::UC::NetworkActivityManager &BasicConnectionSourceAccess::activity(
    const Presonus::UC::BasicConnection &connection) {
  if (!connection.activity_)
    throw std::logic_error("original source-owned connection required");
  return *connection.activity_;
}
Presonus::UC::EventQueue &
BasicConnectionSourceAccess::queue(Presonus::UC::BasicConnection &connection) {
  if (!connection.owned_)
    throw std::logic_error("original source-owned connection required");
  return connection.owned_->queue;
}
OwnedEventQueueState &BasicConnectionSourceAccess::storage(
    Presonus::UC::BasicConnection &connection) {
  if (!connection.owned_)
    throw std::logic_error("original source-owned connection required");
  return *connection.owned_->storage;
}
std::optional<BasicConnectionTypedValues::Binding>
BasicConnectionSourceAccess::bindIncoming(
    Presonus::UC::BasicConnection &connection, Presonus::UC::EventItem &item,
    unsigned type) {
  if (!connection.owned_)
    throw std::logic_error("owned source connection required");
  return connection.owned_->providers.values.bindIncoming(item, type);
}
} // namespace presonus::uc
