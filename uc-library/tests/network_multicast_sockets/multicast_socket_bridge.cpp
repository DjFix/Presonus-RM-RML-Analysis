#include "presonus/uc/multicast_connection.hpp"
#include <arpa/inet.h>
#include <array>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <ifaddrs.h>
#include <iostream>
#include <netdb.h>
#include <new>
#include <string>
#include <sys/select.h>
#include <time.h>
#include <type_traits>
using Posix = Core::Platform::PosixSocket;
using IP = presonus::uc::AdapterIPAddress;
static_assert(std::is_base_of_v<Presonus::UC::BasicConnection,
                                Presonus::UC::MulticastConnection>);
static_assert(
    std::is_same_v<decltype(&Presonus::UC::MulticastConnection::sendEvent),
                   decltype(&Presonus::UC::BasicConnection::sendEvent)>);
struct Allocation {
  void *pointer = nullptr;
  std::size_t size = 0;
  bool live = false;
};
struct ObservedSocket {
  void *pointer = nullptr;
  int descriptor = 0;
  unsigned port = 0;
  bool destroyed = false, freed = false, closed = false;
  std::uint32_t expectedBindIP = 0;
  unsigned expectedBindPort = 0;
};
class ReceiverFixture final : public Presonus::UC::IMulticastReceiver {
public:
  void onMulticastEvent(const char *, unsigned short, unsigned short, int,
                        Presonus::UC::EventItem *) override {
    std::abort(); // Unused fixture callback only; no production default.
  }
};
static std::array<Allocation, 1024> allocations;
static unsigned allocationCount;
static std::array<ObservedSocket, 64> sockets;
static unsigned socketCount;
static int constructing = -1, checking = -1;
static bool active;
static std::uint64_t milliseconds;
static unsigned failures, errors, group;
static std::string trace;
static std::array<std::uint32_t, 3> addresses;
static unsigned addressCount;
struct Telemetry {
  std::uint64_t allocated = 0, destroyed = 0, freed = 0, closed = 0, binds = 0,
                bindFailures = 0, joins = 0, joinFailures = 0,
                localFailures = 0, deviceFailures = 0, interfaceFailures = 0,
                fcntlFailures = 0, selectFailures = 0, socketErrors = 0,
                reusePortUnsupported = 0, clocks = 0;
};
static Telemetry telemetry;
static void require(bool condition) {
  if (!condition)
    std::abort();
}
static std::string hex(const void *pointer, std::size_t size) {
  auto bytes = static_cast<const unsigned char *>(pointer);
  const char alphabet[] = "0123456789abcdef";
  std::string result;
  for (std::size_t n = 0; n < size; ++n) {
    result += alphabet[bytes[n] >> 4];
    result += alphabet[bytes[n] & 15];
  }
  return result;
}
static unsigned identity(const void *pointer) {
  for (unsigned n = 0; n < socketCount; ++n)
    if (sockets[n].pointer == pointer && !sockets[n].freed)
      return n;
  std::abort();
}
static unsigned descriptorIdentity(int descriptor) {
  require(descriptor >= 100 && unsigned(descriptor - 100) < socketCount);
  unsigned id = descriptor - 100;
  require(sockets[id].descriptor == descriptor && !sockets[id].freed);
  return id;
}
extern "C" void *__real__Znwm(std::size_t);
extern "C" void *__wrap__Znwm(std::size_t size) {
  void *result = __real__Znwm(size);
  if (active) {
    require(allocationCount < allocations.size());
    allocations[allocationCount++] = {result, size, true};
  }
  return result;
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
static int deallocationIdentity(void *pointer) {
  for (unsigned n = 0; n < socketCount; ++n)
    if (sockets[n].pointer == pointer && !sockets[n].freed) {
      require(sockets[n].destroyed && sockets[n].closed);
      return n;
    }
  return -1;
}
static void recordDeallocation(int id) {
  if (id < 0)
    return;
  sockets[id].freed = true;
  ++telemetry.freed;
  trace += "F" + std::to_string(id) + ";";
}
static void markAllocationReleased(void *pointer) {
  for (unsigned n = 0; n < allocationCount; ++n)
    if (allocations[n].pointer == pointer)
      allocations[n].live = false;
}
extern "C" void __wrap__ZdlPv(void *pointer) {
  int id = active ? deallocationIdentity(pointer) : -1;
  __real__ZdlPv(pointer);
  if (active)
    markAllocationReleased(pointer);
  recordDeallocation(id);
}
extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  int id = active ? deallocationIdentity(pointer) : -1;
  __real__ZdlPvm(pointer, size);
  if (active)
    markAllocationReleased(pointer);
  recordDeallocation(id);
}
extern "C" void __real__ZN4Core8Platform11PosixSocketC1Eiii(Posix *, int, int,
                                                            int);
extern "C" void __wrap__ZN4Core8Platform11PosixSocketC1Eiii(Posix *self,
                                                            int family,
                                                            int type,
                                                            int protocol) {
  require(active && socketCount < sockets.size());
  bool allocated = false;
  for (unsigned n = 0; n < allocationCount; ++n)
    if (allocations[n].pointer == self && allocations[n].live &&
        allocations[n].size == sizeof(Core::Sockets::Socket))
      allocated = true;
  require(allocated);
  unsigned id = socketCount++;
  sockets[id] = {self, 100 + int(id), 0, false, false, false};
  ++telemetry.allocated;
  trace += "N" + std::to_string(id) + ";C" + std::to_string(id) + ":" +
           std::to_string(family) + ":" + std::to_string(type) + ":" +
           std::to_string(protocol) + ";";
  constructing = id;
  __real__ZN4Core8Platform11PosixSocketC1Eiii(self, family, type, protocol);
  constructing = -1;
}
extern "C" void __real__ZN4Core8Platform11PosixSocketD1Ev(Posix *);
extern "C" void __wrap__ZN4Core8Platform11PosixSocketD1Ev(Posix *self) {
  unsigned id = identity(self);
  require(!sockets[id].destroyed);
  trace += "D" + std::to_string(id) + ";";
  __real__ZN4Core8Platform11PosixSocketD1Ev(self);
  require(sockets[id].closed);
  sockets[id].destroyed = true;
  ++telemetry.destroyed;
}
extern "C" bool __real__ZN4Core8Platform11PosixSocket9setOptionEii(Posix *, int,
                                                                   int);
extern "C" bool __wrap__ZN4Core8Platform11PosixSocket9setOptionEii(Posix *self,
                                                                   int option,
                                                                   int value) {
  unsigned id = identity(self);
  using namespace Core::Sockets;
  int original = option == SocketOption::kReuseAddress ? 104
                 : option == SocketOption::kReusePort  ? 105
                                                       : option;
  require(original == 100 || original == 101 || original == 104 ||
          original == 105);
  trace += "O" + std::to_string(id) + ":" + std::to_string(original) + ":" +
           std::to_string(value) + ";";
  bool result =
      __real__ZN4Core8Platform11PosixSocket9setOptionEii(self, option, value);
  if (option == SocketOption::kReusePort) {
    require(!result);
    ++telemetry.reusePortUnsupported;
  }
  return result;
}
extern "C" bool
__real__ZN4Core8Platform11PosixSocket4bindERKNS_7Sockets11SocketTypes13SocketAddressE(
    Posix *, const Core::Sockets::SocketAddress *);
extern "C" bool
__wrap__ZN4Core8Platform11PosixSocket4bindERKNS_7Sockets11SocketTypes13SocketAddressE(
    Posix *self, const Core::Sockets::SocketAddress *address) {
  auto *ip = IP::cast(const_cast<Core::Sockets::SocketAddress *>(address));
  require(ip && ip->family == 2);
  unsigned id = identity(self);
  sockets[id].expectedBindIP = ip->getIPv4();
  sockets[id].expectedBindPort = ip->port;
  trace += "B" + std::to_string(id) + ":" + std::to_string(ip->getIPv4()) +
           ":" + std::to_string(ip->port) + ";";
  return __real__ZN4Core8Platform11PosixSocket4bindERKNS_7Sockets11SocketTypes13SocketAddressE(
      self, address);
}
extern "C" bool
__real__ZNK4Core8Platform11PosixSocket15getLocalAddressERNS_7Sockets11SocketTypes13SocketAddressE(
    const Posix *, Core::Sockets::SocketAddress *);
extern "C" bool
__wrap__ZNK4Core8Platform11PosixSocket15getLocalAddressERNS_7Sockets11SocketTypes13SocketAddressE(
    const Posix *self, Core::Sockets::SocketAddress *address) {
  bool result =
      __real__ZNK4Core8Platform11PosixSocket15getLocalAddressERNS_7Sockets11SocketTypes13SocketAddressE(
          self, address);
  auto *ip = IP::cast(address);
  require(ip);
  trace += "L" + std::to_string(identity(self)) + ":" +
           std::to_string(ip->port) + ";";
  return result;
}
extern "C" bool
__real__ZN4Core8Platform11PosixSocket18joinMulticastGroupERKNS_7Sockets11SocketTypes9IPAddressES6_(
    Posix *, const IP *, const IP *);
extern "C" bool
__wrap__ZN4Core8Platform11PosixSocket18joinMulticastGroupERKNS_7Sockets11SocketTypes9IPAddressES6_(
    Posix *self, const IP *groupAddress, const IP *adapterAddress) {
  require(groupAddress->family == 2 && adapterAddress->isNull());
  trace += "O" + std::to_string(identity(self)) +
           ":102:" + std::to_string(groupAddress->getIPv4()) + ";";
  return __real__ZN4Core8Platform11PosixSocket18joinMulticastGroupERKNS_7Sockets11SocketTypes9IPAddressES6_(
      self, groupAddress, adapterAddress);
}
extern "C" bool
__real__ZNK4Core8Platform11PosixSocket10isAnyErrorEi(const Posix *, int);
extern "C" bool
__wrap__ZNK4Core8Platform11PosixSocket10isAnyErrorEi(const Posix *self,
                                                     int timeout) {
  unsigned id = identity(self);
  trace += "E" + std::to_string(id) + ":" + std::to_string(timeout) + ";";
  checking = id;
  bool result =
      __real__ZNK4Core8Platform11PosixSocket10isAnyErrorEi(self, timeout);
  checking = -1;
  return result;
}
extern "C" int __wrap_socket(int family, int type, int protocol) {
  require(active && constructing >= 0 && family == AF_INET &&
          type == SOCK_DGRAM && protocol == 17);
  return sockets[constructing].descriptor;
}
extern "C" int __wrap_close(int descriptor) {
  unsigned id = descriptorIdentity(descriptor);
  require(!sockets[id].closed);
  sockets[id].closed = true;
  ++telemetry.closed;
  return 0;
}
extern "C" int __wrap_fcntl(int descriptor, int operation, ...) {
  descriptorIdentity(descriptor);
  if (operation == F_GETFL) {
    if (failures & 32) {
      ++telemetry.fcntlFailures;
      return -1;
    }
    return 0;
  }
  require(operation == F_SETFL);
  va_list args;
  va_start(args, operation);
  int flags = va_arg(args, int);
  va_end(args);
  require(flags & O_NONBLOCK);
  return 0;
}
extern "C" int __wrap_bind(int descriptor, const sockaddr *address,
                           socklen_t size) {
  unsigned id = descriptorIdentity(descriptor);
  require(size == sizeof(sockaddr_in) && address->sa_family == AF_INET);
  auto *ip = reinterpret_cast<const sockaddr_in *>(address);
  require(ip->sin_addr.s_addr == htonl(sockets[id].expectedBindIP) &&
          ip->sin_port == htons(sockets[id].expectedBindPort));
  ++telemetry.binds;
  if (failures & 1) {
    sockets[id].port = 0;
    ++telemetry.bindFailures;
    return -1;
  }
  sockets[id].port = ntohs(ip->sin_port) ? ntohs(ip->sin_port) : 40000 + id;
  return 0;
}
extern "C" int __wrap_getsockname(int descriptor, sockaddr *address,
                                  socklen_t *size) {
  unsigned id = descriptorIdentity(descriptor);
  if (failures & 2) {
    ++telemetry.localFailures;
    return -1;
  }
  require(*size >= sizeof(sockaddr_in));
  auto *ip = reinterpret_cast<sockaddr_in *>(address);
  std::memset(ip, 0, sizeof(*ip));
  ip->sin_family = AF_INET;
  ip->sin_port = htons(sockets[id].port);
  *size = sizeof(*ip);
  return 0;
}
extern "C" int __wrap_setsockopt(int descriptor, int level, int option,
                                 const void *value, socklen_t size) {
  unsigned id = descriptorIdentity(descriptor);
  if (level == IPPROTO_IP) {
    require(option == IP_ADD_MEMBERSHIP && size == sizeof(ip_mreq));
    auto *request = static_cast<const ip_mreq *>(value);
    require(request->imr_multiaddr.s_addr == htonl(group) &&
            request->imr_interface.s_addr == 0);
    ++telemetry.joins;
    if (failures & 4) {
      ++telemetry.joinFailures;
      return -1;
    }
    return 0;
  }
  require(level == SOL_SOCKET);
  if (option == SO_BINDTODEVICE) {
    auto *name = static_cast<const char *>(value);
    require(size == std::strlen(name) + 1);
    trace += "V" + std::to_string(id) + ":" + hex(name, size - 1) + ";";
    if (failures & 32) {
      ++telemetry.deviceFailures;
      return -1;
    }
    return 0;
  }
  require((option == SO_BROADCAST || option == SO_REUSEADDR) &&
          size == sizeof(int) && *static_cast<const int *>(value) == 1);
  return 0;
}
static std::array<ifaddrs, 3> interfaces;
static std::array<sockaddr_in, 3> interfaceIPs;
static char interfaceNames[3][8];
extern "C" int __wrap_getifaddrs(ifaddrs **output) {
  *output = nullptr;
  if (failures & 64) {
    ++telemetry.interfaceFailures;
    return -1;
  }
  for (unsigned n = 0; n < addressCount; ++n) {
    interfaces[n] = {};
    interfaceIPs[n] = {};
    std::snprintf(interfaceNames[n], 8, "eth%u", n);
    interfaces[n].ifa_name = interfaceNames[n];
    interfaces[n].ifa_flags = 0x40;
    interfaces[n].ifa_addr = reinterpret_cast<sockaddr *>(&interfaceIPs[n]);
    interfaces[n].ifa_next =
        n + 1 < addressCount ? &interfaces[n + 1] : nullptr;
    interfaceIPs[n].sin_family = AF_INET;
    interfaceIPs[n].sin_addr.s_addr = htonl(addresses[n]);
  }
  if (addressCount)
    *output = interfaces.data();
  return 0;
}
extern "C" void __wrap_freeifaddrs(ifaddrs *pointer) {
  require(addressCount && pointer == interfaces.data());
}
extern "C" int __wrap_select(int count, fd_set *read, fd_set *write,
                             fd_set *except, timeval *timeout) {
  require(checking >= 0 && read == nullptr && write == nullptr &&
          except != nullptr);
  int fd = sockets[checking].descriptor;
  require(count == fd + 1 && FD_ISSET(fd, except));
  if (timeout)
    require(timeout->tv_sec >= 0 && timeout->tv_usec >= 0 &&
            timeout->tv_usec < 1000000);
  if (failures & 8) {
    ++telemetry.selectFailures;
    return -1;
  }
  FD_ZERO(except);
  if (errors & (1U << checking)) {
    FD_SET(fd, except);
    return 1;
  }
  return 0;
}
extern "C" int __wrap_getsockopt(int descriptor, int level, int option,
                                 void *value, socklen_t *size) {
  descriptorIdentity(descriptor);
  require(level == SOL_SOCKET && option == SO_ERROR && *size >= sizeof(int));
  if (failures & 16) {
    ++telemetry.socketErrors;
    if (descriptor % 2 == 0)
      return -1;
    *static_cast<int *>(value) = 5;
    return 0;
  }
  *static_cast<int *>(value) = 0;
  return 0;
}
extern "C" int __wrap_clock_gettime(clockid_t clock, timespec *value) {
  require(active && clock == CLOCK_MONOTONIC);
  trace += "T;";
  ++telemetry.clocks;
  value->tv_sec = milliseconds / 1000;
  value->tv_nsec = (milliseconds % 1000) * 1000000;
  return 0;
}
extern "C" int __wrap___printf_chk(int, const char *format, ...) {
  char text[1024];
  va_list args;
  va_start(args, format);
  int size = std::vsnprintf(text, sizeof(text), format, args);
  va_end(args);
  require(size >= 0 && size < 1024);
  trace += "R" + hex(text, size) + ";";
  return size;
}
extern "C" int __wrap_getaddrinfo(const char *, const char *, const addrinfo *,
                                  addrinfo **) {
  std::abort();
}
extern "C" hostent *__wrap_gethostbyname(const char *) { std::abort(); }
extern "C" int __wrap_getnameinfo(const sockaddr *, socklen_t, char *,
                                  socklen_t, char *, socklen_t, int) {
  std::abort();
}
extern "C" int __wrap_connect(int, const sockaddr *, socklen_t) {
  std::abort();
}
extern "C" ssize_t __wrap_sendto(int, const void *, std::size_t, int,
                                 const sockaddr *, socklen_t) {
  std::abort();
}
extern "C" ssize_t __wrap_sendmsg(int, const msghdr *, int) { std::abort(); }
static std::string
snapshot(const presonus::uc::MulticastConnectionState &state) {
  return std::to_string(state.unicastEnabled) + " " +
         std::to_string(state.multicastEnabled) + " " +
         std::to_string(state.groupPending) + " " +
         std::to_string(
             static_cast<std::uint64_t>(state.pendingSinceMilliseconds)) +
         " " + std::to_string(state.configuredPort) + " " +
         std::to_string(state.boundPort) + " " +
         std::to_string(state.unicastStorage.count) + " " +
         std::to_string(state.multicastStorage.count) + " " +
         std::to_string(state.receivers.count());
}
int main() {
  std::uint64_t settings[13];
  while (std::cin >> settings[0]) {
    for (unsigned n = 1; n < 10; ++n)
      std::cin >> settings[n];
    std::int64_t timeout;
    std::cin >> timeout >> settings[11] >> settings[12] >> addressCount;
    require(addressCount <= 3);
    for (unsigned n = 0; n < addressCount; ++n)
      std::cin >> addresses[n];
    presonus::uc::CclAdapterServices provider;
    presonus::uc::AdapterHandlerState adapterState(provider);
    adapterState.cacheValid = 1;
    adapterState.multiAddress = settings[0];
    adapterState.storage.count = addressCount;
    for (unsigned n = 0; n < addressCount; ++n)
      adapterState.storage.values[n].setIP(addresses[n]);
    Presonus::UC::AdapterHandler adapter(presonus::uc::AdapterSourcePortTag{},
                                         adapterState);
    presonus::uc::BasicConnectionState outgoing;
    presonus::uc::MulticastConnectionState state(outgoing, adapter,
                                                 adapterState);
    state.configuredPort = settings[1];
    state.boundPort = settings[2];
    state.unicastEnabled = settings[3];
    state.multicastEnabled = settings[4];
    state.groupPending = settings[5];
    std::uint64_t since = settings[6];
    std::memcpy(&state.pendingSinceMilliseconds, &since, 8);
    milliseconds = settings[7];
    failures = settings[8];
    errors = settings[9];
    group = settings[11];
    state.group.setIP(group);
    Presonus::UC::MulticastConnection connection(
        presonus::uc::MulticastSourcePortTag{}, state);
    trace.clear();
    trace.reserve(65536);
    allocationCount = 0;
    socketCount = 0;
    constructing = checking = -1;
    active = true;
    std::array<std::string, 9> snapshots;
    snapshots[0] = snapshot(state);
    connection.setMulticastGroupPending(true);
    snapshots[1] = snapshot(state);
    connection.setMulticastGroupPending(false);
    connection.makeMulticastSockets(true);
    connection.makeUnicastSockets(true);
    snapshots[2] = snapshot(state);
    bool uniError = state.unicast.isAnyError(timeout),
         multiError = state.multicast.isAnyError(timeout);
    connection.startUnicastListening();
    snapshots[3] = snapshot(state);
    ReceiverFixture firstReceiver, absentReceiver;
    Presonus::UC::IMulticastReceiver *first = &firstReceiver;
    auto *second = settings[12] ? first : nullptr;
    connection.addReceiver(first);
    connection.addReceiver(second);
    snapshots[4] = snapshot(state);
    connection.removeReceiver(&absentReceiver);
    connection.removeReceiver(first);
    snapshots[5] = snapshot(state);
    connection.removeReceiver(second);
    connection.removeReceiver(&absentReceiver);
    snapshots[6] = snapshot(state);
    connection.makeUnicastSockets(false);
    connection.startUnicastListening();
    snapshots[7] = snapshot(state);
    connection.makeUnicastSockets(false);
    connection.makeMulticastSockets(false);
    snapshots[8] = snapshot(state);
    for (unsigned n = 0; n < socketCount; ++n)
      require(sockets[n].destroyed && sockets[n].closed && sockets[n].freed);
    active = false;
    for (auto &value : snapshots)
      std::cout << value << '|';
    std::cout << uniError << ' ' << multiError << '|' << trace << '\n';
  }
  std::cerr << "{\"allocated\":" << telemetry.allocated
            << ",\"destroyed\":" << telemetry.destroyed
            << ",\"freed\":" << telemetry.freed
            << ",\"closed\":" << telemetry.closed
            << ",\"binds\":" << telemetry.binds
            << ",\"bindFailures\":" << telemetry.bindFailures
            << ",\"joins\":" << telemetry.joins
            << ",\"joinFailures\":" << telemetry.joinFailures
            << ",\"localFailures\":" << telemetry.localFailures
            << ",\"deviceFailures\":" << telemetry.deviceFailures
            << ",\"interfaceFailures\":" << telemetry.interfaceFailures
            << ",\"fcntlFailures\":" << telemetry.fcntlFailures
            << ",\"selectFailures\":" << telemetry.selectFailures
            << ",\"socketErrors\":" << telemetry.socketErrors
            << ",\"reusePortUnsupported\":" << telemetry.reusePortUnsupported
            << ",\"clocks\":" << telemetry.clocks << "}\n";
}
extern "C" int __wrap_accept(int, sockaddr *, socklen_t *) { std::abort(); }
extern "C" void __wrap_freeaddrinfo(addrinfo *) { std::abort(); }
extern "C" int __wrap_gethostname(char *, std::size_t) { std::abort(); }
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
extern "C" int __wrap_shutdown(int, int) { std::abort(); }
extern "C" int __wrap_pthread_create(pthread_t *, const pthread_attr_t *,
                                     void *(*)(void *), void *) {
  std::abort();
}
