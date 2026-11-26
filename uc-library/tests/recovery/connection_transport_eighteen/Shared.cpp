#include "../../network_services/fixture_manager.hpp"
#include "presonus/uc/ConnectionTransportProvider.hpp"
#include "presonus/uc/MulticastDatagramProvider.hpp"
#include "presonus/uc/basic_connection_runtime.hpp"
#include "presonus/uc/connection_handler.hpp"
#include "presonus/uc/external_connection.hpp"
#include "presonus/uc/network_activity_manager.hpp"
#include "presonus/uc/outgoing_connection.hpp"
#include "presonus/uc/remote_event_sender.hpp"
#include "presonus/uc/report.hpp"
#include "presonus/uc/source_default_factory.hpp"
#include <cassert>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <netdb.h>
#include <netinet/in.h>
#include <string>
#include <string_view>
#include <sys/socket.h>
#include <unistd.h>
#include <vector>
using namespace Presonus::UC;
using namespace presonus::uc;
namespace {
void *watchedDelete = nullptr;
unsigned actualDeletes = 0;
} // namespace
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *pointer) {
  if (pointer == watchedDelete)
    ++actualDeletes;
  __real__ZdlPv(pointer);
}
extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  if (pointer == watchedDelete)
    ++actualDeletes;
  __real__ZdlPvm(pointer, size);
}

namespace {
Presonus::UC::Connection *watchedProcess = nullptr;
unsigned baseProcessEntries = 0, postErrorPolls = 0;
bool forcePostError = false;
std::vector<std::string> capturedReports;
void captureReport(int severity, const char *message) {
  if (severity != 0 || !message)
    std::abort();
  capturedReports.emplace_back(message);
}
} // namespace
extern "C" bool
__real__ZN8Presonus2UC10Connection7processEb(Presonus::UC::Connection *, bool);
extern "C" bool __wrap__ZN8Presonus2UC10Connection7processEb(
    Presonus::UC::Connection *connection, bool drain) {
  if (connection == watchedProcess)
    ++baseProcessEntries;
  return __real__ZN8Presonus2UC10Connection7processEb(connection, drain);
}
extern "C" int __real_select(int, fd_set *, fd_set *, fd_set *, timeval *);
extern "C" int __wrap_select(int n, fd_set *read, fd_set *write, fd_set *error,
                             timeval *timeout) {
  if (watchedProcess && baseProcessEntries && error) {
    ++postErrorPolls;
    if (forcePostError)
      return 1; // Explicit kernel error-readiness fault only.
  }
  return __real_select(n, read, write, error, timeout);
}
extern "C" int __real_getaddrinfo(const char *, const char *, const addrinfo *,
                                  addrinfo **);
extern "C" int __wrap_getaddrinfo(const char *host, const char *service,
                                  const addrinfo *hints, addrinfo **result) {
  if (host && std::strcmp(host, "offline.invalid") == 0)
    return EAI_NONAME;
  if (host && std::strcmp(host, "127.0.0.1") != 0)
    std::abort();
  return __real_getaddrinfo(host, service, hints, result);
}
extern "C" int __real_connect(int, const sockaddr *, socklen_t);
extern "C" int __wrap_connect(int fd, const sockaddr *address, socklen_t size) {
  if (!address || address->sa_family != AF_INET ||
      reinterpret_cast<const sockaddr_in *>(address)->sin_addr.s_addr !=
          htonl(INADDR_LOOPBACK))
    std::abort();
  return __real_connect(fd, address, size);
}
extern "C" ssize_t __real_sendto(int, const void *, size_t, int,
                                 const sockaddr *, socklen_t);
extern "C" ssize_t __wrap_sendto(int fd, const void *data, size_t size,
                                 int flags, const sockaddr *address,
                                 socklen_t length) {
  if (address &&
      (address->sa_family != AF_INET ||
       reinterpret_cast<const sockaddr_in *>(address)->sin_addr.s_addr !=
           htonl(INADDR_LOOPBACK)))
    std::abort();
  return __real_sendto(fd, data, size, flags, address, length);
}
namespace {
#define require(value)                                                         \
  do {                                                                         \
    if (!(value)) {                                                            \
      std::cerr << "failure at " << __LINE__ << "\n";                          \
      std::abort();                                                            \
    }                                                                          \
  } while (false)
struct MemoryChannel final : IDataChannel {
  std::vector<unsigned char> written, input;
  std::vector<int> writeSizes;
  std::size_t cursor = 0;
  bool writable = true, error = false;
  int capacity = 4096, partial = -1;
  bool isReadable(int) override { return cursor < input.size(); }
  int getBytesAvailable() override {
    return static_cast<int>(input.size() - cursor);
  }
  int read(void *data, int n) override {
    const int size = std::min(n, getBytesAvailable());
    std::memcpy(data, input.data() + cursor, size);
    cursor += static_cast<std::size_t>(size);
    return size;
  }
  bool isWritable(int) override { return writable; }
  int getGranularity() override { return capacity; }
  int write(const void *data, int size) override {
    writeSizes.push_back(size);
    auto *bytes = static_cast<const unsigned char *>(data);
    written.insert(written.end(), bytes, bytes + size);
    return partial < 0 ? size : partial;
  }
  bool hasErrors(int) override { return error; }
};
struct SentListener final : ILowLevelNetworkListener {
  unsigned count = 0;
  int type = -1, size = -1;
  std::uint32_t tag = 0;
  bool namePresent = false;
  void sourcePortEventSent(int t, const Event &e, int n,
                           const char *name) override {
    ++count;
    type = t;
    size = n;
    tag = e.type;
    namePresent = name != nullptr;
  }
};
struct QueueFixture {
  BasicConnectionTypedValues values;
  BasicQueueStorage storage;
  EventQueue queue;
  BasicConnectionState state;
  static void *resolve(void *p, const Event &e, QueueValueKind k) {
    auto &self = *static_cast<QueueFixture *>(p);
    return self.values.resolve(e, k, self.storage->items.value());
  }
  explicit QueueFixture(EventFactory &factory)
      : storage(makeBasicQueueStorage(this, resolve)), queue(*storage),
        state{&queue, &factory, &storage->view, storage.get(),
              [](void *p, EventItem *i) {
                static_cast<OwnedEventQueueState *>(p)->append(i);
              }} {}
};
struct LoopbackListener {
  int fd = -1;
  unsigned short port = 0;
  explicit LoopbackListener(int type) {
    fd = ::socket(AF_INET, type,
                  type == SOCK_STREAM ? IPPROTO_TCP : IPPROTO_UDP);
    require(fd >= 0);
    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    require(::bind(fd, reinterpret_cast<sockaddr *>(&address),
                   sizeof(address)) == 0);
    socklen_t size = sizeof(address);
    require(::getsockname(fd, reinterpret_cast<sockaddr *>(&address), &size) ==
            0);
    port = ntohs(address.sin_port);
    timeval timeout{2, 0};
    require(::setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout,
                         sizeof(timeout)) == 0);
    if (type == SOCK_STREAM)
      require(::listen(fd, 1) == 0);
  }
  ~LoopbackListener() {
    if (fd >= 0)
      ::close(fd);
  }
};
struct VisibleOutgoing : OutgoingConnection {
  using OutgoingConnection::OutgoingConnection;
  int descriptor() {
    return static_cast<int>(ownedChannel_->sourceSocket()->getDescriptor());
  }
};
struct OwnedSocketFixture final : SocketConnection {
  explicit OwnedSocketFixture(ConnectionHandler &handler)
      : SocketConnection(handler, 1) {}
  int getType() const override { return 1; }
  void adopt(std::unique_ptr<Core::Sockets::Socket> socket) {
    ownedChannel_ = std::make_unique<Channel>(std::move(socket));
    ConnectionSourceAccess::transport(*this).bind(ownedChannel_.get());
  }
};
struct FrameConnection final : Connection {
  FrameConnection(ConnectionHandler &handler, int type)
      : Connection(handler, type) {}
  int getType() const override { return 1; }
  void getAddress(const char *&text, unsigned short &port) const override {
    text = "127.0.0.1";
    port = 0;
  }
};
int frameCase(ConnectionHandler &handler, const Event &event, int argc,
              char **argv) {
  require(argc == 10);
  MemoryChannel memory;
  const int type = std::atoi(argv[6]);
  FrameConnection connection(handler, type);
  ConnectionSourceAccess::transport(connection).connectionName = "127.0.0.1";
  auto &activity = BasicConnectionSourceAccess::activity(connection);
  auto &projection = NetworkActivityPortAccess::activity(activity).bytes;
  std::uint64_t initialBytes = std::strtoull(argv[8], nullptr, 10),
                initialPackets = std::strtoull(argv[9], nullptr, 10);
  std::memcpy(projection.data() + type * 32 + 16, &initialBytes, 8);
  std::memcpy(projection.data() + type * 32 + 32, &initialPackets, 8);
  std::vector<SentListener> listeners(
      static_cast<unsigned>(std::atoi(argv[7])));
  for (auto &listener : listeners)
    activity.addListener(&listener);
  const int capacity = std::atoi(argv[2]), position = std::atoi(argv[3]);
  memory.partial = std::atoi(argv[4]) ? -1 : 0;
  unsigned char frameStorage[128];
  std::fill(std::begin(frameStorage), std::end(frameStorage), 'B');
  Connection::ChannelWriter writer{memory, frameStorage, capacity, position};
  Event invalid{0xdead, 0, 0, 0};
  const bool success =
      connection.writeEvent(writer, std::atoi(argv[5]) ? event : invalid);
  auto &provider = ConnectionSourceAccess::transport(connection);
  std::uint64_t bytes = 0, packets = 0;
  std::memcpy(&bytes, projection.data() + type * 32 + 16, 8);
  std::memcpy(&packets, projection.data() + type * 32 + 32, 8);
  unsigned observed = 0;
  bool valid = true;
  for (auto &listener : listeners) {
    observed += listener.count;
    valid = valid && (!listener.count ||
                      (listener.type == type && listener.size == 12 &&
                       listener.tag == 20047 && listener.namePresent));
    activity.removeListener(&listener);
  }
  std::cout << success << ' ' << writer.position << ' ' << bytes << ' '
            << packets << ' ' << observed << ' ' << valid;
  for (int n : memory.writeSizes)
    std::cout << ' ' << n;
  std::cout << '\n';
  return 0;
}
int outgoingProcessCase(ConnectionHandler &handler, const Event &event,
                        int argc, char **argv) {
  require(argc == 3);
  const std::string_view mode(argv[2]);
  require(mode == "empty" || mode == "failure" || mode == "success" ||
          mode == "posterror");
  LoopbackListener listener(SOCK_STREAM);
  OutgoingConnection connection(
      handler, mode == "failure" ? "offline.invalid" : "127.0.0.1",
      listener.port, 0);
  if (mode != "empty")
    require(connection.sendEvent(event));
  baseProcessEntries = 0;
  postErrorPolls = 0;
  forcePostError = mode == "posterror";
  watchedProcess = &connection;
  capturedReports.clear();
  UCSetReportFunction(captureReport);
  connection.process(false);
  UCSetReportFunction(nullptr);
  std::vector<std::string> expectedReports;
  if (mode == "failure")
    expectedReports = {"Resolving hostname offline.invalid..."};
  else if (mode != "empty")
    expectedReports = {"Resolving hostname 127.0.0.1...",
                       "Connecting to 127.0.0.1..."};
  if (mode == "posterror")
    expectedReports.push_back("Outgoing socket is in error state!!!");
  require(capturedReports == expectedReports);
  watchedProcess = nullptr;
  forcePostError = false;
  auto &provider = ConnectionSourceAccess::transport(connection);
  const bool channel = provider.channel != nullptr;
  unsigned sent = 0;
  if (channel) {
    const int accepted = ::accept(listener.fd, nullptr, nullptr);
    require(accepted >= 0);
    unsigned char frame[64]{};
    sent = ::recv(accepted, frame, sizeof(frame), 0) == 12;
    ::close(accepted);
  }
  std::cout << baseProcessEntries << ' ' << postErrorPolls << ' '
            << connection.hasQueuedEvents() << ' ' << provider.failed << ' '
            << channel << ' ' << sent << '\n';
  return 0;
}
int resetCase(ConnectionHandler &handler, int argc, char **argv) {
  require(argc == 3);
  const unsigned previous = std::strtoul(argv[2], nullptr, 10);
  require(previous <= 3);
  OutgoingConnection connection(handler, "127.0.0.1", 1, 0);
  for (unsigned i = 0; i < previous; ++i)
    connection.reset();
  auto &provider = ConnectionSourceAccess::transport(connection);
  provider.failed = true;
  const bool result = connection.reset();
  std::cout << result << ' ' << provider.failed << '\n';
  return 0;
}
} // namespace
int main(int argc, char **argv) {
  EventFactory factory;
  BasicConnectionTypedValues values;
  BasicConnectionProviderScope scope(factory, values);
  ConnectionHandlerState handlerState;
  ConnectionHandler handler(handlerState);
  if (argc > 1 && std::string_view(argv[1]) == "reset")
    return resetCase(handler, argc, argv);
  MemoryChannel memory;
  ExternalConnection connection(handler, &memory);
  NoOpEvent value{{20047, 0, 0, 0}};
  auto &codec = DefaultFactoryProvider<
      PrimitiveEventClassNoMembers<NoOpEvent, 20047>>::get();
  codec.bind(value);
  const Event &event = value.header;
  if (argc > 1 && std::string_view(argv[1]) == "process") {
    const int result = outgoingProcessCase(handler, event, argc, argv);
    codec.unbind(value);
    return result;
  }
  if (argc > 1 && std::string_view(argv[1]) == "frame") {
    const int result = frameCase(handler, event, argc, argv);
    codec.unbind(value);
    return result;
  }
  require(!connection.hasQueuedEvents());
  auto &activity = BasicConnectionSourceAccess::activity(connection);
  activity.resetActivity();
  SentListener listener;
  activity.addListener(&listener);
  require(connection.sendEvent(event));
  require(connection.hasQueuedEvents());
  require(connection.process(false));
  require(!connection.hasQueuedEvents());
  require(memory.written.size() == 12);
  require(listener.count == 1 && listener.type == 3 && listener.size == 12 &&
          listener.tag == 20047 && listener.namePresent);
  std::uint64_t bytes = 0, packets = 0;
  const auto &activityBytes = activity.getActivityInfo().bytes;
  std::memcpy(&bytes, activityBytes.data() + 112, 8);
  std::memcpy(&packets, activityBytes.data() + 128, 8);
  require(bytes == 12 && packets == 1);
  activity.removeListener(&listener);
  const unsigned char header[6] = {'U', 'C', 0, 1, 6, 0};
  require(
      std::equal(memory.written.begin(), memory.written.begin() + 6, header));
  auto *queued = factory.create(event);
  require(queued && connection.queueEvent(queued));
  memory.partial = 0;
  require(!connection.process(false));
  require(ConnectionSourceAccess::transport(connection).failed);
  memory.partial = -1;
  memory.writable = false;
  require(connection.sendEvent(event));
  connection.process(true);
  require(!connection.hasQueuedEvents());
  // Default owning and independent borrowed raw-head queries remain separate.
  EventQueueState raw;
  BasicConnectionState borrowed;
  borrowed.storage = &raw;
  BasicConnection borrowedConnection(borrowed);
  require(!borrowedConnection.hasQueuedEvents());
  EventQueueNode node;
  raw.head = &node;
  require(borrowedConnection.hasQueuedEvents());
  // Reset has the native bounded three-success retry policy with real owning
  // construction and no activation/network operation.
  {
    OutgoingConnection empty(handler, nullptr, 0, 0);
    const char *host = nullptr;
    unsigned short port = 1;
    empty.getAddress(host, port);
    require(host && !*host && port == 0);
    std::string input(300, 'a');
    OutgoingConnection longName(handler, input.c_str(), 65535, 65535);
    longName.getAddress(host, port);
    require(std::strlen(host) == 255 && port == 65535);
  }
  OutgoingConnection outgoing(handler, "127.0.0.1", 12345, 23456);
  require(outgoing.reset());
  require(outgoing.reset());
  require(outgoing.reset());
  require(!outgoing.reset());
  // Independent native control-flow branches with genuine source queues and
  // bounded in-memory I/O; no expected values are computed by the new method.
  for (bool drain : {false, true}) {
    MemoryChannel broken;
    broken.input = {'X', 'X', 0, 1, 0, 0};
    ExternalConnection pending(handler, &broken);
    require(pending.sendEvent(event));
    pending.process(drain);
    require(pending.hasQueuedEvents() == !drain);
    require(ConnectionSourceAccess::transport(pending).failed == !drain);
  }
  {
    FrameConnection inactive(handler, 1);
    require(inactive.sendEvent(event));
    require(inactive.process(false));
    require(!inactive.hasQueuedEvents());
    MemoryChannel blocked;
    blocked.writable = false;
    ExternalConnection pending(handler, &blocked);
    require(pending.sendEvent(event));
    require(pending.process(false));
    require(pending.hasQueuedEvents());
    require(pending.process(true));
    require(!pending.hasQueuedEvents());
  }
  {
    MemoryChannel error;
    error.error = true;
    ExternalConnection failed(handler, &error);
    capturedReports.clear();
    UCSetReportFunction(captureReport);
    require(!failed.process(false));
    UCSetReportFunction(nullptr);
    require(capturedReports == std::vector<std::string>{
                                   "External connection is in error state!!!"});
  }
  // Actual current receive factory -> owned incoming queue -> dispatcher.
  memory.input = {'U', 'C', 0, 1, 6, 0, 0x4e, 0x4f, 47, 0, 0, 0};
  ConnectionSourceAccess::transport(connection).failed = false;
  require(connection.process(false));
  auto &dispatcher = ConnectionSourceAccess::dispatcher(connection);
  require(dispatcher.hasEvents());
  auto *received = DispatcherSourceAccess::state(dispatcher).retrieve();
  require(received && received->getData().type == 20047);
  require(ConnectionSourceAccess::senderCount(connection) == 1);
  auto *nativeSender =
      static_cast<RemoteEventSender *>(connection.findSender(47));
  require(nativeSender &&
          received->getData().routeA ==
              static_cast<std::uint32_t>(nativeSender->sourcePortIDs().local));
  require(connection.makeLocalID(47) == nativeSender->sourcePortIDs().local);
  delete received;
  connection.removeSender(47);
  {
    MemoryChannel input;
    ExternalConnection receiver(handler, &input);
    ParamValueEvent parameter{};
    parameter.header = {20566, 152, 0, 0};
    parameter.path[0] = 'a';
    parameter.index = 7;
    auto &provider = DefaultFactoryProvider<ParamValueEventClass>::get();
    provider.bind(parameter);
    for (unsigned number : {11u, 42u}) {
      parameter.valueBits = number;
      unsigned char wire[256]{};
      const int size = factory.write(reinterpret_cast<char *>(wire),
                                     sizeof(wire), parameter.header);
      require(size > 0);
      const unsigned char frame[6] = {'U',
                                      'C',
                                      0,
                                      1,
                                      static_cast<unsigned char>(size),
                                      static_cast<unsigned char>(size >> 8)};
      input.input.insert(input.input.end(), frame, frame + 6);
      input.input.insert(input.input.end(), wire, wire + size);
    }
    provider.unbind(parameter);
    require(receiver.process(false));
    auto *updated = DispatcherSourceAccess::state(dispatcher).retrieve();
    auto *typed = dynamic_cast<TypedEventItem<ParamValueEvent> *>(updated);
    require(typed && typed->value.valueBits == 42 && !dispatcher.hasEvents());
    delete updated;
  }
  {
    MemoryChannel loop;
    ExternalConnection roundtrip(handler, &loop);
    unsigned char payload[5] = {9, 8, 7, 6, 5};
    OwnedDataPayload<LoopbackQueryEvent> query;
    query.header = {19537, 24, 0, 0};
    query.data = payload;
    query.sizeBits = sizeof(payload);
    auto &queryCodec = DefaultFactoryProvider<
        DataEventClass<LoopbackQueryEvent, 19537>>::get();
    queryCodec.bind(query);
    unsigned char wire[128]{};
    const int length = factory.write(reinterpret_cast<char *>(wire),
                                     sizeof(wire), query.header);
    queryCodec.unbind(query);
    require(length > 0);
    loop.input = {'U',
                  'C',
                  0,
                  1,
                  static_cast<unsigned char>(length),
                  static_cast<unsigned char>(length >> 8)};
    loop.input.insert(loop.input.end(), wire, wire + length);
    require(roundtrip.process(false));
    require(roundtrip.hasQueuedEvents());
    std::fill(std::begin(payload), std::end(payload), 0);
    require(roundtrip.process(false));
    require(!roundtrip.hasQueuedEvents());
    require(loop.written.size() > 6);
    std::unique_ptr<EventItem> reply(
        factory.read(reinterpret_cast<const char *>(loop.written.data() + 6),
                     static_cast<int>(loop.written.size() - 6)));
    auto *typed =
        dynamic_cast<OwnedCodecItem<OwnedDataPayload<LoopbackReplyEvent>> *>(
            reply.get());
    const unsigned char expected[5] = {9, 8, 7, 6, 5};
    require(typed && typed->value.sizeBits == 5 &&
            std::memcmp(typed->value.data, expected, 5) == 0);
  }
  // An actual owning CCL TCP connection is restricted to fresh loopback.
  {
    LoopbackListener listener(SOCK_STREAM);
    LoopbackListener udp(SOCK_DGRAM);
    CclAdapterServices services;
    AdapterHandlerState adapterState(services);
    adapterState.cacheValid = 1;
    adapterState.storage.count = 1;
    adapterState.storage.values[0].setIP(127, 0, 0, 1, 0);
    AdapterHandler adapter(AdapterSourcePortTag{}, adapterState);
    QueueFixture tagged(factory);
    MulticastConnectionState multicastState(tagged.state, adapter,
                                            adapterState);
    multicastState.broadcast.setIP(127, 0, 0, 1, udp.port);
    multicastState.unicastEnabled = 1;
    auto *udpSocket = new Core::Sockets::Socket(Core::Sockets::kInternet,
                                                Core::Sockets::kDatagram,
                                                Core::Sockets::kUDP);
    AdapterIPAddress local;
    local.setIP(127, 0, 0, 1, 0);
    require(udpSocket->bind(local));
    multicastState.unicastStorage.sockets[0] = udpSocket;
    multicastState.unicastStorage.count = 1;
    MulticastConnection multicast(MulticastSourcePortTag{}, multicastState);
    handlerState.multicastIdentity = &multicast;
    handlerState.multicastOutgoing = &multicast;
    NetworkManagerState managerState{
        ConnectionSourceAccess::dispatcher(connection), factory};
    managerState.connectionHandler = &handler;
    FixtureManager manager(managerState);
    require(!manager.hasOutgoingEvents());
    require(multicast.queueEvent(factory.create(event)));
    require(multicast.hasQueuedEvents() && manager.hasOutgoingEvents());
    require(manager.NetworkManager::waitForOutgoingEvents(0) == 0);
    multicast.process(true);
    require(!multicast.hasQueuedEvents() && !manager.hasOutgoingEvents());
    unsigned char queuedPacket[64]{};
    require(::recv(udp.fd, queuedPacket, sizeof(queuedPacket), 0) == 12);
    VisibleOutgoing real(handler, "127.0.0.1", listener.port, 0);
    require(real.activate());
    const int descriptor = real.descriptor();
    const int accepted = ::accept(listener.fd, nullptr, nullptr);
    require(accepted >= 0);
    require(real.sendEvent(event));
    require(real.process(false));
    unsigned char packet[64]{};
    require(::recv(accepted, packet, sizeof(packet), 0) == 12);
    require(std::equal(packet, packet + 6, header));
    capturedReports.clear();
    UCSetReportFunction(captureReport);
    require(real.sendPeriodicEvent(event));
    require(
        capturedReports ==
        std::vector<std::string>{"Can't send periodic event to 127.0.0.1!!!"});
    capturedReports.clear();
    // Learn the UDP mapping through the actual TCP receive/typed factory path.
    unsigned char mapping[14] = {'U',
                                 'C',
                                 0,
                                 1,
                                 8,
                                 0,
                                 0x55,
                                 0x4d,
                                 0,
                                 0,
                                 0,
                                 0,
                                 static_cast<unsigned char>(udp.port),
                                 static_cast<unsigned char>(udp.port >> 8)};
    require(::send(accepted, mapping, sizeof(mapping), 0) == sizeof(mapping));
    require(real.process(false));
    UCSetReportFunction(nullptr);
    require(capturedReports ==
            std::vector<std::string>{"UDP mapping for 127.0.0.1 set to " +
                                     std::to_string(udp.port)});
    require(real.sendPeriodicEvent(event));
    unsigned char datagram[64]{};
    require(::recv(udp.fd, datagram, sizeof(datagram), 0) == 12);
    const unsigned char udpHeader[6] = {'U', 'C', 0, 1, 0, 0};
    require(std::equal(datagram, datagram + 6, udpHeader));
    auto &realDispatcher = ConnectionSourceAccess::dispatcher(real);
    auto *sender = real.addSender(73);
    value.header.routeB =
        static_cast<std::uint32_t>(sender->sourcePortIDs().local);
    require(manager.sendEvent(value.header, 1) == 0);
    require(realDispatcher.hasEvents());
    realDispatcher.dispatchAll();
    require(real.hasQueuedEvents());
    require(real.process(false));
    require(!real.hasQueuedEvents());
    require(::recv(udp.fd, datagram, sizeof(datagram), 0) == 12);
    // Only exact flag1 uses UDP. Flag2 comes from the same real manager.
    require(manager.sendEvent(value.header, 2) == 0);
    realDispatcher.dispatchAll();
    require(real.process(false));
    require(::recv(accepted, packet, sizeof(packet), 0) == 12);
    require(::recv(udp.fd, datagram, sizeof(datagram), MSG_DONTWAIT) == -1 &&
            (errno == EAGAIN || errno == EWOULDBLOCK));
    // The public Basic coalescer retains the first item's actual producer
    // flags while destroying the later item and updating its payload.
    ParamValueEvent parameter{};
    parameter.header = {
        20566, 152, 0,
        static_cast<std::uint32_t>(sender->sourcePortIDs().local)};
    parameter.path[0] = 'a';
    parameter.index = 7;
    parameter.valueBits = 11;
    auto &paramCodec = DefaultFactoryProvider<ParamValueEventClass>::get();
    paramCodec.bind(parameter);
    auto origin =
        DispatcherSourceAccess::values(realDispatcher).bind(parameter);
    require(manager.sendEvent(parameter.header, 1) == 0);
    realDispatcher.dispatchAll();
    parameter.valueBits = 42;
    require(manager.sendEvent(parameter.header, 2) == 0);
    realDispatcher.dispatchAll();
    require(real.process(false));
    const int paramSize =
        static_cast<int>(::recv(udp.fd, datagram, sizeof(datagram), 0));
    require(paramSize > 6);
    std::unique_ptr<EventItem> updated(
        factory.read(reinterpret_cast<char *>(datagram + 6), paramSize - 6));
    auto *param =
        dynamic_cast<TypedEventItem<ParamValueEvent> *>(updated.get());
    require(param && param->value.valueBits == 42);
    require(::recv(accepted, packet, sizeof(packet), MSG_DONTWAIT) == -1 &&
            (errno == EAGAIN || errno == EWOULDBLOCK));
    paramCodec.unbind(parameter);
    memory.writable = true;
    memory.written.clear();
    ConnectionSourceAccess::transport(connection).failed = false;
    auto *externalSender = connection.addSender(81);
    value.header.routeB =
        static_cast<std::uint32_t>(externalSender->sourcePortIDs().local);
    require(manager.sendEvent(value.header, 1) == 0);
    realDispatcher.dispatchAll();
    require(connection.process(false) && memory.written.size() == 12);
    value.header.routeB = 0;
    multicast.cleanup();
    handlerState.multicastIdentity = nullptr;
    handlerState.multicastOutgoing = nullptr;
    // A real partial frame survives channel deactivation, as in the native
    // lifecycle; bind does not silently clear the pending receive state.
    const unsigned char partialHeader[6] = {'U', 'C', 0, 1, 6, 0};
    require(::send(accepted, partialHeader, 6, 0) == 6);
    require(real.readEvents());
    require(ConnectionSourceAccess::transport(real).receive.pending == 1);
    real.deactivate();
    require(ConnectionSourceAccess::transport(real).receive.pending == 1);
    require(::fcntl(descriptor, F_GETFD) == -1 && errno == EBADF);
    ::close(accepted);
  }
  {
    LoopbackListener listener(SOCK_STREAM);
    OutgoingConnection lazy(handler, "127.0.0.1", listener.port, 0);
    require(lazy.sendEvent(event));
    require(lazy.process(false));
    require(!lazy.hasQueuedEvents());
    const int accepted = ::accept(listener.fd, nullptr, nullptr);
    require(accepted >= 0);
    require(lazy.process(false));
    require(!lazy.hasQueuedEvents());
    unsigned char packet[64]{};
    require(::recv(accepted, packet, sizeof(packet), 0) == 12);
    lazy.deactivate();
    ::close(accepted);
    OutgoingConnection rejected(handler, "offline.invalid", listener.port, 0);
    require(!rejected.activate());
    require(rejected.sendEvent(event));
    require(rejected.process(false) && !rejected.hasQueuedEvents());
  }
  // Default owning multicast also uses a real fresh UDP socket whose sole
  // configured destination is loopback. Source-port setup changes no ARM
  // layout.
  {
    LoopbackListener udp(SOCK_DGRAM);
    MulticastConnection owned;
    auto &state = const_cast<MulticastConnectionState &>(
        MulticastDatagramProvider(owned).sourceState());
    state.broadcast.setIP(127, 0, 0, 1, udp.port);
    state.unicastEnabled = 1;
    auto *socket = new Core::Sockets::Socket(Core::Sockets::kInternet,
                                             Core::Sockets::kDatagram,
                                             Core::Sockets::kUDP);
    AdapterIPAddress local;
    local.setIP(127, 0, 0, 1, 0);
    require(socket->bind(local));
    state.unicastStorage.sockets[0] = socket;
    state.unicastStorage.count = 1;
    require(owned.queueEvent(factory.create(event)));
    require(owned.hasQueuedEvents());
    owned.process(true);
    require(!owned.hasQueuedEvents());
    unsigned char packet[64]{};
    require(::recv(udp.fd, packet, sizeof(packet), 0) == 12);
    require(::recv(udp.fd, packet, sizeof(packet), 0) == 12);
    owned.cleanup();
  }
  {
    auto socket = std::make_unique<Core::Sockets::Socket>(
        Core::Sockets::kInternet, Core::Sockets::kStream, Core::Sockets::kTCP);
    const int descriptor = static_cast<int>(socket->getDescriptor());
    {
      OwnedSocketFixture owner(handler);
      owner.adopt(std::move(socket));
    }
    require(::fcntl(descriptor, F_GETFD) == -1 && errno == EBADF);
  }
  // Observe actual global deallocation performed by emitted deleting
  // destructors, never a manually appended "delete" event.
  {
    auto *heap = new ExternalConnection(handler, &memory);
    watchedDelete = heap;
    actualDeletes = 0;
    delete heap;
    require(actualDeletes == 1);
    watchedDelete = nullptr;
    auto *out = new OutgoingConnection(handler, "127.0.0.1", 1, 0);
    watchedDelete = out;
    actualDeletes = 0;
    delete out;
    require(actualDeletes == 1);
    watchedDelete = nullptr;
    auto socket = std::make_unique<Core::Sockets::Socket>(
        Core::Sockets::kInternet, Core::Sockets::kStream, Core::Sockets::kTCP);
    const int descriptor = static_cast<int>(socket->getDescriptor());
    auto *channel = new SocketConnection::Channel(std::move(socket));
    watchedDelete = channel;
    actualDeletes = 0;
    delete channel;
    require(actualDeletes == 1);
    watchedDelete = nullptr;
    require(::fcntl(descriptor, F_GETFD) == -1 && errno == EBADF);
  }
  codec.unbind(value);
  std::cout << "positive enqueue/query/process, frame, partial-write, drain "
               "and retry passed\n";
}
