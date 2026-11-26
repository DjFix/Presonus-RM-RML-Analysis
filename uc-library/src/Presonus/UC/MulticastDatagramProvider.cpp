#include "presonus/uc/MulticastDatagramProvider.hpp"
#include "presonus/uc/ccl_bindings.hpp"
#include "presonus/uc/udp_discovery.hpp"
#include <memory>
#include <stdexcept>
namespace presonus::uc {
MulticastDatagramProvider::MulticastDatagramProvider(
    Presonus::UC::MulticastConnection &connection)
    : connection_(connection), state_(connection.state_) {}
void MulticastDatagramProvider::normalizeAddress(
    Presonus::UC::AdapterHandler &adapter, AdapterIPAddress &address) {
  const auto &cache = adapter.sourcePortState();
  if (cache.cacheValid && cache.storage.count == 1 &&
      cache.storage.values[0].isNull() && address.isLoopback())
    address = AdapterIPAddress{};
}
bool MulticastDatagramProvider::isLocalAddress(
    Presonus::UC::AdapterHandler &adapter, const AdapterIPAddress &address) {
  adapter.getAddressList(false);
  const auto &cache = adapter.sourcePortState().storage;
  for (int index = 0; index < cache.count; ++index)
    if (cache.values[index] == address)
      return true;
  return false;
}
void MulticastDatagramProvider::bindReceiver(
    Presonus::UC::IMulticastReceiver &receiver,
    MulticastReceiveDisposition &disposition) {
  for (int i = 0; i < state_.receiverBindings.count(); ++i)
    if (state_.receiverBindings.at(i).identity == &receiver) {
      state_.receiverBindings.at(i).disposition = &disposition;
      return;
    }
  if (!state_.receiverBindings.add({&receiver, &disposition}))
    throw std::bad_alloc();
}
bool MulticastDatagramProvider::sendTo(const AdapterIPAddress &address,
                                       const Presonus::UC::Event &event) {
  if (!state_.unicastEnabled)
    connection_.makeUnicastSockets(true);
  if (state_.unicastStorage.count == 0)
    return true;
  bool sent = false;
  for (int i = 0; i < state_.unicastStorage.count; ++i) {
    auto &socket = *state_.unicastStorage.sockets[i];
    if (socket.isWritable(10) && writeEvent(socket, address, event))
      sent = true;
  }
  return sent;
}
bool MulticastDatagramProvider::writeEvent(Core::Sockets::Socket &socket,
                                           const AdapterIPAddress &address,
                                           const Presonus::UC::Event &event) {
  if (!state_.outgoing.factory)
    throw std::logic_error("Actual EventFactory provider required");
  Core::IO::Buffer buffer;
  if (!buffer.resize(16384))
    throw std::bad_alloc();
  CclBufferViews views(buffer);
  auto writer = views.writer(16384);
  const unsigned char header[6] = {
      'U',
      'C',
      0,
      1,
      static_cast<unsigned char>(state_.boundPort),
      static_cast<unsigned char>(state_.boundPort >> 8)};
  if (!writer->writeRaw(header, 6) ||
      !state_.outgoing.factory->write(*writer, event))
    return false;
  const int size = writer->position();
  return socket.sendTo(buffer.getAddress(), size, address) == size;
}
bool MulticastDatagramProvider::readEvent(Core::Sockets::Socket &socket) {
  if (!state_.outgoing.factory)
    throw std::logic_error("Actual EventFactory provider required");
  Core::IO::Buffer buffer;
  if (!buffer.resize(16384))
    throw std::bad_alloc();
  AdapterIPAddress address;
  int size = socket.receiveFrom(buffer.getAddress(), 16384, address);
  if (size <= 0)
    return false;
  normalizeAddress(state_.adapter, address);
  const auto sourcePort = address.port;
  address.port = 0;
  CclBufferViews views(buffer);
  auto reader = views.reader(static_cast<unsigned>(size));
  unsigned char header[6]{};
  if (size < 2 || !reader->readRaw(header, 2) || header[0] != 'U' ||
      header[1] != 'C')
    return false;
  if (size < 4 || !reader->readRaw(header + 2, 2))
    return true;
  if (header[2] != 0 || header[3] != 1)
    return true;
  if (size < 6 || !reader->readRaw(header + 4, 2))
    return true;
  const unsigned short senderPort =
      header[4] | static_cast<unsigned short>(header[5] << 8);
  std::unique_ptr<Presonus::UC::EventItem> item(
      state_.outgoing.factory->read(*reader));
  if (!item)
    return true;
  Core::CStringBuffer<256> host;
  Core::Sockets::Network::getAddressString(host, address);
  const int locality =
      senderPort == state_.boundPort && isLocalAddress(state_.adapter, address)
          ? 0
          : 1;
  for (int i = 0; i < state_.receivers.count(); ++i) {
    auto *receiver = state_.receivers.at(i);
    MulticastReceiveDisposition *provider = nullptr;
    for (int j = 0; j < state_.receiverBindings.count(); ++j)
      if (state_.receiverBindings.at(j).identity == receiver)
        provider = state_.receiverBindings.at(j).disposition;
    if (provider) {
      // Provider borrows until a true return. It must neither retain on false
      // nor destroy on false/throw. On true ownership transfers and must be
      // released before returning to the caller; throwing leaves ownership
      // here.
      if (provider->receive(host.str(), senderPort, sourcePort, locality,
                            *item)) {
        item.release();
        return true;
      }
    } else if (auto *discovery =
                   dynamic_cast<Presonus::UC::UDPDiscoveryHandler *>(
                       receiver)) {
      discovery->onMulticastEvent(host.str(), senderPort, sourcePort, locality,
                                  item.get());
    } else
      throw std::logic_error(
          "Unknown void receiver requires explicit ownership disposition");
  }
  return true;
}
} // namespace presonus::uc
