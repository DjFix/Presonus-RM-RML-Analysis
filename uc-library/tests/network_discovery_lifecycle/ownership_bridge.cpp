#include "presonus/uc/ccl_bindings.hpp"
#include "presonus/uc/discovery_ownership.hpp"
#include "presonus/uc/multicast_connection.hpp"
#include "presonus/uc/no_member_events.hpp"
#include <array>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <ifaddrs.h>
#include <iostream>
#include <netdb.h>
#include <new>
#include <string>
using namespace presonus::uc;
using namespace Presonus::UC;
static void require(bool condition) {
  if (!condition)
    std::abort();
}
static std::string trace;
struct OwnerSlot {
  UDPDiscoveryEntry *view = nullptr;
  void *allocation = nullptr;
  bool freed = false;
};
static std::array<OwnerSlot, 8> slots;
static unsigned total;
static bool tracking, capturing;
static void *captured;
static std::uint64_t allocations, frees, sendCalls, appendCalls;
static DiscoveryHandlerState *handlerState;
static DiscoveryEntryOwnership *ownership;
static BasicConnection *expectedBasic;
static IMulticastReceiver *expectedReceiver;
static std::string hex(const void *pointer, unsigned length) {
  const auto *p = static_cast<const unsigned char *>(pointer);
  const char alphabet[] = "0123456789abcdef";
  std::string s;
  for (unsigned n = 0; n < length; ++n) {
    s += alphabet[p[n] >> 4];
    s += alphabet[p[n] & 15];
  }
  return s;
}
static unsigned identity(const UDPDiscoveryEntry *view) {
  for (unsigned n = 0; n < total; ++n)
    if (slots[n].view == view)
      return n;
  std::abort();
}
extern "C" void *__real__Znwm(std::size_t);
extern "C" void *__wrap__Znwm(std::size_t size) {
  auto *p = __real__Znwm(size);
  if (capturing) {
    require(!captured);
    captured = p;
    ++allocations;
  }
  return p;
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
static int deletion(void *pointer) {
  if (!tracking)
    return -1;
  for (unsigned n = 0; n < total; ++n)
    if (slots[n].allocation == pointer && !slots[n].freed)
      return n;
  return -1;
}
static void freed(int id) {
  if (id < 0)
    return;
  slots[id].freed = true;
  ++frees;
  trace += "D" + std::to_string(id) + ";";
}
extern "C" void __wrap__ZdlPv(void *pointer) {
  int id = deletion(pointer);
  __real__ZdlPv(pointer);
  freed(id);
}
extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  int id = deletion(pointer);
  __real__ZdlPvm(pointer, size);
  freed(id);
}
extern "C" void
__real__ZN8Presonus2UC19MulticastConnection11addReceiverEPNS0_18IMulticastReceiverE(
    MulticastConnection *, IMulticastReceiver *);
extern "C" void
__wrap__ZN8Presonus2UC19MulticastConnection11addReceiverEPNS0_18IMulticastReceiverE(
    MulticastConnection *connection, IMulticastReceiver *receiver) {
  require(receiver == expectedReceiver);
  trace += "A;";
  __real__ZN8Presonus2UC19MulticastConnection11addReceiverEPNS0_18IMulticastReceiverE(
      connection, receiver);
}
extern "C" void
__real__ZN8Presonus2UC19MulticastConnection14removeReceiverEPNS0_18IMulticastReceiverE(
    MulticastConnection *, IMulticastReceiver *);
extern "C" void
__wrap__ZN8Presonus2UC19MulticastConnection14removeReceiverEPNS0_18IMulticastReceiverE(
    MulticastConnection *connection, IMulticastReceiver *receiver) {
  require(receiver == expectedReceiver);
  trace += "B;";
  __real__ZN8Presonus2UC19MulticastConnection14removeReceiverEPNS0_18IMulticastReceiverE(
      connection, receiver);
}
extern "C" bool __real__ZN8Presonus2UC15BasicConnection9sendEventERKNS0_5EventE(
    BasicConnection *, const Event *);
extern "C" bool __wrap__ZN8Presonus2UC15BasicConnection9sendEventERKNS0_5EventE(
    BasicConnection *connection, const Event *event) {
  require(connection == expectedBasic);
  trace += "S" + std::to_string(event->type) + ":" +
           std::to_string(event->reserved04) + ":" +
           std::to_string(event->routeA) + ":" + std::to_string(event->routeB) +
           ";";
  ++sendCalls;
  return __real__ZN8Presonus2UC15BasicConnection9sendEventERKNS0_5EventE(
      connection, event);
}
class HandlerFixture final : public UDPDiscoveryHandler {
public:
  using UDPDiscoveryHandler::UDPDiscoveryHandler;
  bool registerServer(void *&, const DiscoveryDescriptor &, int) override {
    std::abort();
  }
  void processDiscovery() override { std::abort(); }
  void onMulticastEvent(const char *, unsigned short, unsigned short, int,
                        EventItem *) override {
    std::abort();
  }
};
class Keeper final : public IMulticastReceiver {
public:
  void onMulticastEvent(const char *, unsigned short, unsigned short, int,
                        EventItem *) override {
    std::abort();
  }
};
class Reply final : public IDiscoveryReplyHandler {
public:
  void onRegistrationCompleted(void *) override { std::abort(); }
  void onServerAdded(void *, const DiscoveryDescriptor &) override {
    std::abort();
  }
  void onServerChanged(void *, const char *) override { std::abort(); }
  void onServerRemoved(void *pointer) override {
    auto *view = static_cast<UDPDiscoveryEntry *>(pointer);
    unsigned id = identity(view);
    require(!slots[id].freed);
    ownership->stateFor(view);
    trace += "R" + std::to_string(id) + ":" +
             std::to_string(handlerState->entries.count()) + ":" +
             std::to_string(handlerState->counter28) + ":" +
             std::to_string(handlerState->counter2c) + ";";
  }
};
struct QueueContext {
  Core::Vector<EventItem *> items;
  std::array<EventQueueNode, 16> nodes;
  EventQueueState *state = nullptr;
};
static void append(void *p, EventItem *item) {
  auto &context = *static_cast<QueueContext *>(p);
  int index = context.items.count();
  require(index < 16 && context.items.add(item));
  context.nodes[index] = {item, nullptr};
  if (index)
    context.nodes[index - 1].next = &context.nodes[index];
  else
    context.state->head = &context.nodes[index];
  trace += "Q;";
  ++appendCalls;
}
static void pattern(char *data, unsigned seed, unsigned length,
                    unsigned capacity) {
  for (unsigned n = 0; n < capacity; ++n)
    data[n] = 33 + (seed + n * 7) % 90;
  data[length] = 0;
  data[capacity - 1] = 0;
}
static std::int32_t signedBits(std::uint32_t bits) {
  std::int32_t value;
  std::memcpy(&value, &bits, 4);
  return value;
}
static std::string snapshot(const MulticastConnectionState &mc,
                            const DiscoveryHandlerState &state) {
  std::string value =
      std::to_string(mc.receivers.count()) + " " +
      std::to_string(ownership->count()) + " " +
      std::to_string(state.entries.count()) + " " +
      std::to_string(state.counter28) + " " + std::to_string(state.counter2c) +
      " " +
      std::to_string(
          static_cast<QueueContext *>(mc.outgoing.context)->items.count());
  for (int n = 0; n < state.entries.count(); ++n)
    value += " " + std::to_string(identity(state.entries.at(n)));
  return value;
}
extern bool ownershipStartup(IDiscoveryHandler &, bool);
extern void ownershipRestart(IDiscoveryHandler &);
extern void ownershipShutdown(IDiscoveryHandler &);
extern void ownershipUnregister(IDiscoveryHandler &, void *);
int main() {
  std::uint64_t settings[10];
  while (std::cin >> settings[0]) {
    for (unsigned n = 1; n < 10; ++n)
      std::cin >> settings[n];
    std::cin >> total;
    require(total >= 2 && total <= 8);
    DiscoveryEntryOwnership owners;
    ownership = &owners;
    DiscoveryHandlerState state;
    handlerState = &state;
    state.ownership = &owners;
    state.counter28 = settings[8];
    state.counter2c = settings[9];
    Reply reply;
    state.reply = &reply;
    Core::Threads::Lock lock;
    EventQueueState queueState;
    queueState.context = &lock;
    queueState.lock = [](void *p) {
      static_cast<Core::Threads::Lock *>(p)->lock();
    };
    queueState.unlock = [](void *p) {
      static_cast<Core::Threads::Lock *>(p)->unlock();
    };
    queueState.value = [](void *, const Event &, QueueValueKind) -> void * {
      std::abort();
    };
    EventQueue queue(queueState);
    CclFactoryRegistry registry;
    FactoryCodec codec;
    codec.clone = [](void *, const Event &event) -> EventItem * {
      auto *item = new TypedEventItem<DiscoveryLeaveEvent>;
      item->value.header = event;
      return item;
    };
    codec.create = [](void *) -> EventItem * {
      return new TypedEventItem<DiscoveryLeaveEvent>;
    };
    codec.destroy = [](void *, EventItem *item) { delete item; };
    codec.write = [](void *, BufferWriter &, const Event &) -> bool {
      std::abort();
    };
    codec.read = [](void *, EventItem *, BufferReader &) -> bool {
      std::abort();
    };
    if (settings[7])
      registry.registry().append(17484, &codec);
    EventFactory factory(registry.registry());
    QueueContext context;
    context.state = &queueState;
    BasicConnectionState outgoing;
    outgoing.queue = &queue;
    outgoing.factory = &factory;
    outgoing.storage = &queueState;
    outgoing.context = &context;
    outgoing.append = append;
    CclAdapterServices services;
    AdapterHandlerState adapterState(services);
    adapterState.cacheValid = 1;
    AdapterHandler adapter(AdapterSourcePortTag{}, adapterState);
    MulticastConnectionState mcState(outgoing, adapter, adapterState);
    MulticastConnection connection(MulticastSourcePortTag{}, mcState);
    state.connection = &connection;
    Keeper keeper;
    require(mcState.receivers.add(&keeper));
    expectedBasic = static_cast<BasicConnection *>(&connection);
    HandlerFixture handler(DiscoverySourcePortTag{}, state);
    expectedReceiver = static_cast<IMulticastReceiver *>(&handler);
    tracking = false;
    for (unsigned n = 0; n < total; ++n) {
      unsigned flag0, flag3, flag4, length;
      std::uint32_t identifier;
      std::cin >> flag0 >> flag3 >> flag4 >> identifier >> length;
      captured = nullptr;
      capturing = true;
      auto *view = owners.create();
      capturing = false;
      require(captured);
      slots[n] = {view, captured, false};
      auto &entry = owners.stateFor(view);
      entry.flag0 = flag0;
      entry.flag3 = flag3;
      entry.flag4 = flag4;
      entry.dirty = 77;
      entry.identifier = signedBits(identifier);
      pattern(entry.displayName.getBuffer(), settings[0] + n * 13 + 3, length,
              64);
      if (n < total - 2)
        require(state.entries.add(view));
    }
    trace.clear();
    trace.reserve(4096);
    tracking = true;
    char external[512];
    pattern(external, settings[0] + 19, settings[5], 512);
    const char *name =
        settings[2] == 0 ? nullptr
        : settings[2] == 1
            ? external
            : owners.stateFor(slots[settings[2] == 2 || settings[2] == 3
                                        ? settings[1]
                                        : settings[3]]
                                  .view)
                      .displayName.str() +
                  (settings[2] == 3 ? settings[4] : 0);
    bool changed = slots[settings[1]].view->updateHostName(name);
    std::array<std::string, 8> names;
    for (unsigned n = 0; n < total; ++n)
      names[n] = hex(owners.stateFor(slots[n].view).displayName.str(), 64);
    require(ownershipStartup(handler, settings[0] & 1));
    if (settings[6])
      require(ownershipStartup(handler, true));
    std::array<std::string, 6> images;
    images[0] = snapshot(mcState, state);
    handler.removeServer(slots[total - 2].view);
    images[1] = snapshot(mcState, state);
    ownershipUnregister(handler, slots[total - 1].view);
    images[2] = snapshot(mcState, state);
    ownershipRestart(handler);
    images[3] = snapshot(mcState, state);
    ownershipShutdown(handler);
    images[4] = snapshot(mcState, state);
    if (settings[6])
      ownershipShutdown(handler);
    images[5] = snapshot(mcState, state);
    require(owners.count() == 0 && mcState.receivers.count() == 1);
    for (unsigned n = 0; n < total; ++n)
      require(slots[n].freed);
    tracking = false;
    std::cout << changed << '|';
    for (unsigned n = 0; n < total; ++n)
      std::cout << names[n] << '|';
    for (auto &image : images)
      std::cout << image << '|';
    std::cout << trace << '\n';
    for (int n = 0; n < context.items.count(); ++n)
      delete context.items.at(n);
  }
  std::cerr << "{\"owned_allocations\":" << allocations
            << ",\"actual_free_forwards\":" << frees
            << ",\"actual_basic_send_calls\":" << sendCalls
            << ",\"actual_queue_appends\":" << appendCalls << "}\n";
}
// Keeper guarantees no first/last socket transitions in these new owning cases;
// complete MC742 real Socket/error/deletion cases are separately replayed.
extern "C" int __wrap_socket(int, int, int) { std::abort(); }
extern "C" int __wrap_connect(int, const sockaddr *, socklen_t) {
  std::abort();
}
extern "C" int __wrap_bind(int, const sockaddr *, socklen_t) { std::abort(); }
extern "C" int __wrap_close(int) { std::abort(); }
extern "C" int __wrap_setsockopt(int, int, int, const void *, socklen_t) {
  std::abort();
}
extern "C" int __wrap_fcntl(int, int, ...) { std::abort(); }
extern "C" int __wrap_getsockname(int, sockaddr *, socklen_t *) {
  std::abort();
}
extern "C" int __wrap_getsockopt(int, int, int, void *, socklen_t *) {
  std::abort();
}
extern "C" int __wrap_select(int, fd_set *, fd_set *, fd_set *, timeval *) {
  std::abort();
}
extern "C" int __wrap_accept(int, sockaddr *, socklen_t *) { std::abort(); }
extern "C" int __wrap_getpeername(int, sockaddr *, socklen_t *) {
  std::abort();
}
extern "C" int __wrap_ioctl(int, unsigned long, ...) { std::abort(); }
extern "C" int __wrap_listen(int, int) { std::abort(); }
extern "C" ssize_t __wrap_recv(int, void *, std::size_t, int) { std::abort(); }
extern "C" ssize_t __wrap_recvfrom(int, void *, std::size_t, int, sockaddr *,
                                   socklen_t *) {
  std::abort();
}
extern "C" ssize_t __wrap_send(int, const void *, std::size_t, int) {
  std::abort();
}
extern "C" ssize_t __wrap_sendto(int, const void *, std::size_t, int,
                                 const sockaddr *, socklen_t) {
  std::abort();
}
extern "C" ssize_t __wrap_sendmsg(int, const msghdr *, int) { std::abort(); }
extern "C" int __wrap_shutdown(int, int) { std::abort(); }
extern "C" int __wrap_gethostname(char *, std::size_t) { std::abort(); }
extern "C" int __wrap_pthread_create(pthread_t *, const pthread_attr_t *,
                                     void *(*)(void *), void *) {
  std::abort();
}

extern "C" int __wrap_getifaddrs(ifaddrs **) { std::abort(); }
extern "C" void __wrap_freeifaddrs(ifaddrs *) { std::abort(); }
extern "C" int __wrap_getaddrinfo(const char *, const char *, const addrinfo *,
                                  addrinfo **) {
  std::abort();
}
extern "C" void __wrap_freeaddrinfo(addrinfo *) { std::abort(); }
extern "C" int __wrap_getnameinfo(const sockaddr *, socklen_t, char *,
                                  socklen_t, char *, socklen_t, int) {
  std::abort();
}
extern "C" hostent *__wrap_gethostbyname(const char *) { std::abort(); }
extern "C" int __wrap_clock_gettime(clockid_t, timespec *) { std::abort(); }
