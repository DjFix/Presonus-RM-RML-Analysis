#include "connection_fixture.hpp"
#include "fixture_manager.hpp"
#include "presonus/uc/ccl_bindings.hpp"
#include "presonus/uc/typed_factory_codec.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <map>
using namespace Presonus::UC;
namespace {
void require(bool value) {
  if (!value)
    throw std::runtime_error("loopback service check");
}
struct Outgoing final : IEventHandler {
  EventFactory &factory;
  presonus::uc::ParamValueFactoryCodec &codec;
  SocketConnection::Channel &channel;
  std::map<EventItem *, int> &flags;
  unsigned calls = 0;
  Outgoing(EventFactory &f, presonus::uc::ParamValueFactoryCodec &c,
           SocketConnection::Channel &s, std::map<EventItem *, int> &v)
      : factory(f), codec(c), channel(s), flags(v) {}
  int handleEvent(void *context, const Event &event) override {
    auto *item = dynamic_cast<presonus::uc::TypedEventItem<ParamValueEvent> *>(
        static_cast<EventItem *>(context));
    require(item && &item->value.header == &event && flags.at(item) == 7);
    codec.bind(item->value);
    std::array<char, 256> frame{};
    const int bytes = factory.write(frame.data() + 6, frame.size() - 6, event);
    codec.unbind(item->value);
    require(bytes > 0 && bytes <= 250);
    frame[0] = 'U';
    frame[1] = 'C';
    frame[2] = 0;
    frame[3] = 1;
    frame[4] = static_cast<char>(bytes);
    frame[5] = static_cast<char>(bytes >> 8);
    require(channel.isWritable(1000) &&
            channel.write(frame.data(), bytes + 6) == bytes + 6);
    flags.erase(item);
    ++calls;
    return 0;
  }
};
} // namespace
int main() {
  try {
    using namespace Core::Sockets;
    Socket listener(kInternet, kStream, kTCP);
    IPAddress address;
    address.setIP(127, 0, 0, 1, 0);
    require(address.isLoopback() && listener.bind(address) &&
            listener.listen(1));
    IPAddress bound;
    require(listener.getLocalAddress(bound) && bound.isLoopback() &&
            bound.port != 0);
    Socket client(kInternet, kStream, kTCP);
    require(client.connect(bound) && listener.isReadable(1000));
    const auto accepted = listener.accept();
    require(accepted >= 0);
    Socket server(accepted);
    IPAddress clientPeer, serverPeer;
    require(client.getPeerAddress(clientPeer) &&
            server.getPeerAddress(serverPeer) && clientPeer.isLoopback() &&
            serverPeer.isLoopback());
    presonus::uc::CclSocketChannel sender(client), receiver(server);
    presonus::uc::CclFactoryRegistry registry;
    presonus::uc::ParamValueFactoryCodec codec;
    codec.registerIn(registry.registry());
    EventFactory factory(registry.registry());
    presonus::uc::EventDispatcherState dispatcherState;
    EventDispatcher dispatcher(dispatcherState);
    presonus::uc::NetworkManagerState state{dispatcher, factory};
    std::map<EventItem *, int> flags;
    state.context = &flags;
    state.storeFlags = [](void *p, EventItem &item, int value) {
      static_cast<std::map<EventItem *, int> *>(p)->emplace(&item, value);
    };
    state.reportOversized = [](void *) {
      throw std::runtime_error("unexpected oversize");
    };
    FixtureManager network(state);
    Outgoing outgoing(factory, codec, sender.channel(), flags);
    int identifier = -1;
    require(network.registerHandler(identifier, &outgoing) == 0 &&
            identifier == 100);
    ParamValueEvent event{};
    event.header = {20566, 152, 123, static_cast<unsigned>(identifier)};
    std::strcpy(event.path.data(), "/actual-network-services/loopback");
    event.index = 65535;
    event.valueBits = 0x7f812345;
    codec.bind(event);
    require(network.sendEvent(event.header, 7) == 0);
    codec.unbind(event);
    require(dispatcherState.queued.count() == 1);
    dispatcher.dispatchAll();
    require(outgoing.calls == 1 && flags.empty());
    require(receiver.channel().isReadable(1000));
    Core::Threads::Lock lock;
    Core::IO::Buffer buffer(Core::uint32(16390));
    EventItem *received = nullptr;
    presonus::uc::CclReceiveProviders providers(
        receiver, lock, factory, &received, [](void *p, EventItem *item) {
          auto &r = *static_cast<EventItem **>(p);
          require(!r);
          r = item;
        });
    presonus::uc::ConnectionReceiveState incoming;
    require(providers.bind(incoming, buffer));
    presonus::uc::ConnectionState common;
    common.receive = &incoming;
    hierarchy_test::ConcreteConnection connection(common);
    require(connection.readEvents());
    auto *typed =
        dynamic_cast<presonus::uc::TypedEventItem<ParamValueEvent> *>(received);
    require(typed && typed->value.header.routeA == 123 &&
            typed->value.header.routeB == 100 && typed->value.index == 65535 &&
            typed->value.valueBits == event.valueBits &&
            !std::strcmp(typed->value.path.data(), event.path.data()));
    delete received;
    require(network.unregisterHandler(&outgoing) == 0);
    require(client.disconnect() && server.disconnect() &&
            listener.disconnect());
    std::cout << "127.0.0.1 only: real NetworkManager send/registration -> CCL "
                 "dispatcher/factory -> CCL Socket/UC framing -> real "
                 "receive/codec PASS\n";
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
