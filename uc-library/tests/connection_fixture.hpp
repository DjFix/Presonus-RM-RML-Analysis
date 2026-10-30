#pragma once
#include "presonus/uc/basic_connection_runtime.hpp"
#include "presonus/uc/ccl_bindings.hpp"
#include "presonus/uc/connection.hpp"
#include "presonus/uc/external_connection.hpp"
#include <cstdlib>
// Dedicated TEST adapter; no production fake implementations of original pure
// slots. Real Core queue/mutex, actual factory, typed value resolution and
// ownership state outlive every borrowed BasicConnection base.
namespace hierarchy_test {
struct LiveBasicState {
  presonus::uc::BasicConnectionTypedValues values;
  presonus::uc::BasicQueueStorage storage;
  Presonus::UC::EventQueue queue;
  presonus::uc::BasicConnectionState basic;
  static void *resolve(void *p, const Presonus::UC::Event &event,
                       presonus::uc::QueueValueKind kind) {
    auto &self = *static_cast<LiveBasicState *>(p);
    return self.values.resolve(event, kind, self.storage->items.value());
  }
  LiveBasicState()
      : storage(presonus::uc::makeBasicQueueStorage(this, resolve)),
        queue(*storage) {
    basic.queue = &queue;
    basic.factory = &presonus::uc::cclFactoryHolder().factory;
    basic.storage = &storage->view;
    basic.context = storage.get();
    basic.append = [](void *p, Presonus::UC::EventItem *item) {
      static_cast<presonus::uc::OwnedEventQueueState *>(p)->append(item);
    };
  }
};
class ConcreteConnection : private LiveBasicState,
                           public Presonus::UC::Connection {
public:
  explicit ConcreteConnection(presonus::uc::ConnectionState &state)
      : Presonus::UC::Connection(state, LiveBasicState::basic) {}
  bool process(bool) override { std::abort(); }
  int getType() const override { return -113; }
  void getAddress(const char *&address, unsigned short &port) const override {
    address = "test-adapter";
    port = 113;
  }
};
class ConcreteExternalConnection : public Presonus::UC::ExternalConnection {
public:
  ConcreteExternalConnection(presonus::uc::ExternalConnectionState &state,
                             presonus::uc::ConnectionState &common,
                             presonus::uc::BasicConnectionState &basic)
      : ExternalConnection(state, common, basic) {}
  bool process(bool) override { std::abort(); }
};
} // namespace hierarchy_test
