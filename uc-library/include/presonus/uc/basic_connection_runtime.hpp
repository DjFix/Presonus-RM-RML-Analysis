#pragma once
#include "presonus/uc/activity_singleton.hpp"
#include "presonus/uc/basic_connection.hpp"
#include "presonus/uc/typed_factory_codec.hpp"
#include <optional>

namespace presonus::uc {
// Independent live-type provenance, not an original layout/cast provider.
// External bound values have stable addresses and outlive their binding and
// all synchronous calls. Queued values are actual TypedEventItem<T> objects.
// The source API is serialized; no concurrent registration/mutation guarantee.
class BasicConnectionTypedValues {
  struct State;
  std::shared_ptr<State> state_;
  void bindValue(Presonus::UC::Event &, void *, QueueValueKind);

public:
  class Binding {
    friend class BasicConnectionTypedValues;
    std::shared_ptr<State> state_;
    const Presonus::UC::Event *header_ = nullptr;
    Binding(std::shared_ptr<State>, const Presonus::UC::Event *);

  public:
    Binding(Binding &&) noexcept = default;
    Binding(const Binding &) = delete;
    Binding &operator=(const Binding &) = delete;
    Binding &operator=(Binding &&) = delete;
    ~Binding();
  };
  BasicConnectionTypedValues();
  ~BasicConnectionTypedValues();
  BasicConnectionTypedValues(const BasicConnectionTypedValues &) = delete;
  BasicConnectionTypedValues &
  operator=(const BasicConnectionTypedValues &) = delete;
  Binding bind(Presonus::UC::ParamValueEvent &);
  Binding bind(Presonus::UC::ParamIncrementEvent &);
  Binding bind(Presonus::UC::ParamColorEvent &);
  Binding bind(Presonus::UC::ParamStringEvent &);
  Binding bind(Presonus::UC::ParamStringListEvent &);
  Binding bind(Presonus::UC::ParamRangeEvent &);
  Binding bind(Presonus::UC::FileDataRateEvent &);
  Binding bind(Presonus::UC::TimeCodeEvent &);
  std::optional<Binding> bindIncoming(Presonus::UC::EventItem &, unsigned type);
  void *
  resolve(const Presonus::UC::Event &, QueueValueKind,
          const Core::IntrusiveLinkedList<Presonus::UC::EventItem> &) const;
};

// Independent storage factory keeps actual SDK mutex instantiation/destruction
// in its own provider unit. Basic/test/interface code retains vptr sanitizer.
struct BasicQueueStorageDeleter {
  void operator()(OwnedEventQueueState *) const;
};
using BasicQueueStorage =
    std::unique_ptr<OwnedEventQueueState, BasicQueueStorageDeleter>;
BasicQueueStorage makeBasicQueueStorage(void *,
                                        OwnedEventQueueState::ValueProvider);

struct BasicConnectionProviders {
  Presonus::UC::EventFactory &factory;
  BasicConnectionTypedValues &values;
};
// Explicit dependency contract: install one real, initialized factory and
// typed-value source before BasicConnection(int). Both outlive all connections.
// No default null factory, fake success callback or source Core class exists.
// Missing scope throws; this is an intentional portable bootstrap requirement,
// not a claim that original factory singleton initialization is recovered.
class BasicConnectionProviderScope {
  BasicConnectionProviders providers_;

public:
  BasicConnectionProviderScope(Presonus::UC::EventFactory &,
                               BasicConnectionTypedValues &);
  ~BasicConnectionProviderScope();
  BasicConnectionProviderScope(const BasicConnectionProviderScope &) = delete;
  BasicConnectionProviderScope &
  operator=(const BasicConnectionProviderScope &) = delete;
};

struct BasicConnectionSourceAccess {
  static int connectionType(const Presonus::UC::BasicConnection &);
  static Presonus::UC::NetworkActivityManager &
  activity(const Presonus::UC::BasicConnection &);
  static Presonus::UC::EventQueue &queue(Presonus::UC::BasicConnection &);
  static OwnedEventQueueState &storage(Presonus::UC::BasicConnection &);
  static std::optional<BasicConnectionTypedValues::Binding>
  bindIncoming(Presonus::UC::BasicConnection &, Presonus::UC::EventItem &,
               unsigned type);
};
} // namespace presonus::uc
