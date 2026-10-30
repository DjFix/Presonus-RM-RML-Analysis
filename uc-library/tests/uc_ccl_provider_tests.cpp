#include "connection_fixture.hpp"
#include "presonus/uc/ccl_bindings.hpp"
#include "presonus/uc/typed_factory_codec.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <sys/socket.h>
#include <thread>

using namespace presonus::uc;
using namespace Presonus::UC;
static void checked(bool v, int line) {
  if (!v)
    throw std::runtime_error("CCL binding check failed at line " +
                             std::to_string(line));
}
#define require(value) checked((value), __LINE__)
static void storage() {
  Core::IO::Buffer empty;
  CclBufferViews emptyViews(empty);
  require(emptyViews.reader(0).has_value());
  require(emptyViews.writer(0).has_value());
  require(!emptyViews.reader(0, 1) && !emptyViews.writer(1));
  Core::IO::Buffer data(Core::uint32(16));
  CclBufferViews views(data);
  auto writer = views.writer(16, 2);
  require(writer && writer->write<unsigned short>(0xa1b2));
  auto reader = views.reader(4, 2);
  unsigned short value = 0;
  require(reader && reader->read(value) && value == 0xa1b2 &&
          reader->position() == 4);
  require(!views.reader(17) && !views.reader(16, 17));
  Core::IO::Buffer copy(data.getAddress(), data.getSize(), true);
  require(copy.getAddress() != data.getAddress() && copy.getSize() == 16);
  require(!std::memcmp(copy.getAddress(), data.getAddress(), 16));
}
static void synchronization() {
  Core::Threads::Lock lock;
  unsigned value = 0;
  auto work = [&] {
    for (unsigned i = 0; i < 2000; ++i) {
      Core::Threads::ScopedLock guard(lock);
      ++value;
    }
  };
  std::thread a(work), b(work);
  a.join();
  b.join();
  require(value == 4000 && lock.tryLock());
  lock.unlock();
}
static void registry() {
  CclFactoryRegistry backend;
  auto &registry = backend.registry();
  FactoryCodec a{}, b{};
  registry.fallback = &b;
  registry.append(-1, &a);
  registry.append(-1, &b);
  registry.append(7, nullptr);
  // get distinguishes an existing null from a missing key and first duplicate
  // wins, even when signed IDs normalize to the same CCL storage bucket.
  require(registry.sourceBackendGet);
  const FactoryCodec *found = nullptr;
  require(registry.sourceBackendGet(registry.sourceBackendContext, found, -1) &&
          found == &a);
  require(registry.sourceBackendGet(registry.sourceBackendContext, found, 7) &&
          found == nullptr);
  require(!registry.sourceBackendGet(registry.sourceBackendContext, found, 15));
  require(backend.remove(-1));
  require(registry.sourceBackendGet(registry.sourceBackendContext, found, -1) &&
          found == &b);
  require(&cclFactoryHolder() == &cclFactoryHolder());
}
struct Received {
  EventItem *item = nullptr;
  unsigned observers = 0;
};
static void socketAndReceive() {
  int descriptors[2];
  require(::socketpair(AF_UNIX, SOCK_STREAM, 0, descriptors) == 0);
  Core::Sockets::Socket incoming(descriptors[0]), outgoing(descriptors[1]);
  CclSocketChannel receiver(incoming), sender(outgoing);
  require(sender.channel().isWritable(1) && !receiver.channel().isReadable(0));
  ParamValueFactoryCodec codec;
  CclFactoryRegistry registry;
  codec.registerIn(registry.registry());
  EventFactory factory(registry.registry());
  ParamValueEvent event{};
  event.header = {20566, 0, 0x12345678, 0x87654321};
  std::strcpy(event.path.data(), "/real-ccl");
  event.index = 65535;
  event.valueBits = 0x7f812345;
  codec.bind(event);
  std::array<char, 256> frame{};
  const int n = factory.write(frame.data() + 6, frame.size() - 6, event.header);
  require(n > 0 && n <= 250);
  frame[0] = 'U';
  frame[1] = 'C';
  frame[2] = 0;
  frame[3] = 1;
  frame[4] = static_cast<char>(n);
  frame[5] = static_cast<char>(n >> 8);
  require(sender.channel().write(frame.data(), n + 6) == n + 6);
  require(receiver.channel().isReadable(1) &&
          receiver.channel().getBytesAvailable() == n + 6);
  Core::Threads::Lock lock;
  Core::IO::Buffer buffer(Core::uint32(16390));
  Received received;
  CclReceiveProviders providers(receiver, lock, factory, &received,
                                [](void *p, EventItem *item) {
                                  auto &r = *static_cast<Received *>(p);
                                  require(!r.item && r.observers == 1);
                                  r.item = item;
                                });
  ConnectionReceiveState state;
  require(providers.bind(state, buffer));
  state.connectionIndex = 7;
  state.connectionName = "actual-ccl";
  ConnectionReceiveObserver observer{
      &received,
      [](void *p, int index, const Event &e, int n, const char *name) {
        require(index == 7 && e.routeA == 0x5678 && e.routeB == 0x4321 &&
                n > 0 && !std::strcmp(name, "actual-ccl"));
        ++static_cast<Received *>(p)->observers;
      }};
  state.observerCount = 1;
  state.observers = &observer;
  ConnectionState common;
  common.receive = &state;
  hierarchy_test::ConcreteConnection connection(common);
  require(connection.readEvents());
  auto *typed = dynamic_cast<TypedEventItem<ParamValueEvent> *>(received.item);
  require(typed && typed->value.valueBits == event.valueBits &&
          typed->value.index == 65535);
  require(state.receivedBytes == unsigned(n) && state.receivedEvents == 1 &&
          !state.pending);
  require(!receiver.channel().hasErrors(0) &&
          receiver.channel().getGranularity() == 4096);
  delete received.item;
  codec.unbind(event);
}
int main() {
  storage();
  synchronization();
  registry();
  socketAndReceive();
  std::cout
      << "4 actual CCL Buffer/Lock/HashMap/Socket-framing groups passed\n";
}
