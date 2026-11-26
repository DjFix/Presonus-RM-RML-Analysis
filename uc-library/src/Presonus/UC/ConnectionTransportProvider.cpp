#include "presonus/uc/ConnectionTransportProvider.hpp"
#include "presonus/uc/basic_connection_runtime.hpp"
#include "presonus/uc/typed_factory_codec.hpp"
#include <new>
namespace presonus::uc {
ConnectionTransportProvider::ConnectionTransportProvider(
    Presonus::UC::Connection &c)
    : connection(c) {
  if (!receiveBuffer.resize(16384) || !writeBuffer.resize(16384 + 6))
    throw std::bad_alloc();
  receive.buffer = &receiveBuffer;
  receive.context = this;
  receive.readable = [](void *p, int timeout) {
    auto *channel = static_cast<ConnectionTransportProvider *>(p)->channel;
    return channel && channel->isReadable(timeout);
  };
  receive.available = [](void *p) {
    return static_cast<ConnectionTransportProvider *>(p)
        ->channel->getBytesAvailable();
  };
  receive.read = [](void *p, void *data, int size) {
    return static_cast<ConnectionTransportProvider *>(p)->channel->read(data,
                                                                        size);
  };
  receive.factory = [](void *p) -> Presonus::UC::EventFactory & {
    return static_cast<ConnectionTransportProvider *>(p)->factory;
  };
  receive.append = [](void *p, Presonus::UC::EventItem *item) {
    auto &self = *static_cast<ConnectionTransportProvider *>(p);
    if (auto *mapping =
            dynamic_cast<TypedEventItem<Presonus::UC::UDPMappingEvent> *>(item))
      self.mappingPorts.emplace(&item->getData(), mapping->value.mapping);
    ConnectionSourceAccess::incoming(self.connection).append(item);
  };
}
void ConnectionTransportProvider::bind(Presonus::UC::IDataChannel *value) {
  channel = value;
  receive.connectionIndex =
      BasicConnectionSourceAccess::connectionType(connection);
  receive.connectionName = connectionName.str();
  // Native deactivate/activate preserve partial receive framing state.
  if (channel)
    connection.initChannel();
}
} // namespace presonus::uc

#include "presonus/uc/network_activity_manager.hpp"
#include <cstring>
#include <stdexcept>
namespace presonus::uc {
void NetworkActivityPortAccess::recordSent(
    Presonus::UC::NetworkActivityManager &manager, int type,
    const Presonus::UC::Event &event, int bytes, const char *name) {
  if (type < 0 || type > 3 || bytes < 0)
    throw std::invalid_argument(
        "initialized Connection activity type required");
  auto add = [&](std::size_t offset, std::uint64_t increment) {
    std::uint64_t count;
    std::memcpy(&count, manager.activity_.bytes.data() + offset, sizeof(count));
    count += increment;
    std::memcpy(manager.activity_.bytes.data() + offset, &count, sizeof(count));
  };
  // Original manager+8 is the explicitly documented projection origin; these
  // are projection indices, never offsets applied to the host C++ object.
  add(static_cast<std::size_t>(type) * 32 + 16,
      static_cast<std::uint64_t>(bytes));
  add(static_cast<std::size_t>(type) * 32 + 32, 1);
  if (!manager.listeners_.count())
    return;
  Core::Threads::ScopedLock guard(manager.lock_);
  const int count = manager.listeners_.count();
  for (int index = 0; index < count; ++index)
    manager.listeners_.at(index)->sourcePortEventSent(type, event, bytes, name);
}
} // namespace presonus::uc
