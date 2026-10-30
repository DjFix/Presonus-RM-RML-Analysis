#include "presonus/uc/adapter_handler.hpp"
#include <arpa/inet.h>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ifaddrs.h>
#include <iostream>
#include <netdb.h>
#include <sstream>
#include <string>
#include <vector>
using namespace presonus::uc;
struct Row {
  int family, flags;
  std::uint32_t value;
  unsigned port;
};
struct Snapshot {
  bool fail;
  std::vector<Row> rows;
};
static Snapshot snapshots[2];
static unsigned lookup;
static bool hostFail, formatFail;
static std::string host, trace;
static std::vector<ifaddrs> interfaces;
static std::vector<sockaddr_in6> addresses;
static std::string hex(const void *data, std::size_t count) {
  static const char digits[] = "0123456789abcdef";
  std::string result;
  auto p = static_cast<const unsigned char *>(data);
  for (std::size_t n = 0; n < count; ++n) {
    result += digits[p[n] >> 4];
    result += digits[p[n] & 15];
  }
  return result;
}
extern "C" int __wrap_getifaddrs(ifaddrs **output) {
  trace += "G;";
  const auto &snapshot = snapshots[lookup++ % 2];
  *output = nullptr;
  if (snapshot.fail)
    return -1;
  interfaces.assign(snapshot.rows.size(), {});
  addresses.assign(snapshot.rows.size(), {});
  for (std::size_t n = 0; n < interfaces.size(); ++n) {
    const auto &row = snapshot.rows[n];
    auto &item = interfaces[n];
    item.ifa_next = n + 1 < interfaces.size() ? &interfaces[n + 1] : nullptr;
    item.ifa_flags = row.flags;
    if (row.family) {
      item.ifa_addr = reinterpret_cast<sockaddr *>(&addresses[n]);
      item.ifa_addr->sa_family = row.family;
      if (row.family == AF_INET) {
        auto *v = reinterpret_cast<sockaddr_in *>(&addresses[n]);
        v->sin_addr.s_addr = htonl(row.value);
        v->sin_port = htons(row.port);
      }
    }
  }
  if (!interfaces.empty())
    *output = interfaces.data();
  return 0;
}
extern "C" void __wrap_freeifaddrs(ifaddrs *value) {
  if (value != interfaces.data() || interfaces.empty())
    std::abort();
  trace += "F;";
}
extern "C" int __wrap_gethostname(char *output, std::size_t size) {
  trace += "H;";
  if (hostFail)
    return -1;
  if (host.size() >= size)
    std::abort();
  std::memcpy(output, host.c_str(), host.size() + 1);
  return 0;
}
extern "C" const char *__real_inet_ntop(int, const void *, char *, socklen_t);
extern "C" const char *__wrap_inet_ntop(int family, const void *address,
                                        char *output, socklen_t size) {
  trace += "T;";
  if (family != AF_INET)
    std::abort();
  if (formatFail)
    return nullptr;
  return __real_inet_ntop(family, address, output, size);
}
extern "C" int __wrap___printf_chk(int, const char *format, ...) {
  char text[1024];
  va_list args;
  va_start(args, format);
  int n = std::vsnprintf(text, sizeof(text), format, args);
  va_end(args);
  if (n < 0 || n >= 1024)
    std::abort();
  trace += "R" + hex(text, n) + ";";
  return n;
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
extern "C" int __wrap_socket(int, int, int) { std::abort(); }
extern "C" int __wrap_connect(int, const sockaddr *, socklen_t) {
  std::abort();
}
extern "C" ssize_t __wrap_sendto(int, const void *, std::size_t, int,
                                 const sockaddr *, socklen_t) {
  std::abort();
}
extern "C" ssize_t __wrap_sendmsg(int, const msghdr *, int) { std::abort(); }
static void setAddress(AdapterIPAddress &address, std::uint32_t value,
                       unsigned port) {
  static_assert(sizeof(AdapterIPAddress) == 36);
  unsigned char bytes[36] = {};
  std::uint32_t size = 36, family = 2;
  std::memcpy(bytes, &size, 4);
  std::memcpy(bytes + 4, &family, 4);
  std::uint16_t p = port;
  std::memcpy(bytes + 8, &p, 2);
  for (int n = 0; n < 4; ++n)
    bytes[12 + n] = value >> (24 - 8 * n);
  std::memcpy(&address, bytes, 36);
}
static void readList(AdapterAddressListState &state) {
  std::cin >> state.count;
  if (state.count < 0 || state.count > 10)
    std::abort();
  for (int n = 0; n < 10; ++n) {
    std::uint32_t value = 0;
    unsigned port = 0;
    if (n < state.count)
      std::cin >> value >> port;
    setAddress(state.values[n], value, port);
  }
}
static void seed(Core::CStringBuffer<256> &text, unsigned value,
                 unsigned length) {
  for (unsigned n = 0; n < 256; ++n)
    text.getBuffer()[n] = 65 + (value + n) % 26;
  text.getBuffer()[length] = 0;
}
static std::uint32_t eligible(const Snapshot &snapshot, bool last) {
  std::uint32_t value = 0;
  for (auto &row : snapshot.rows)
    if (row.family == 2 && (row.flags & 0x40) && !(row.flags & 8)) {
      value = row.value;
      if (!last)
        break;
    }
  return value;
}
static std::string ipText(std::uint32_t value) {
  return std::to_string(value >> 24) + "." +
         std::to_string((value >> 16) & 255) + "." +
         std::to_string((value >> 8) & 255) + "." + std::to_string(value & 255);
}
int main() {
  std::uint64_t settings[15];
  while (std::cin >> settings[0]) {
    for (int n = 1; n < 15; ++n)
      std::cin >> settings[n];
    CclAdapterServices provider;
    AdapterHandlerState state(provider);
    readList(state.storage);
    AdapterAddressListState copied = state.storage, other;
    readList(other);
    for (auto &snapshot : snapshots) {
      int fail, count;
      std::cin >> fail >> count;
      snapshot.fail = fail;
      snapshot.rows.resize(count);
      for (auto &row : snapshot.rows)
        std::cin >> row.family >> row.flags >> row.value >> row.port;
    }
    unsigned seedValue = settings[14];
    host.clear();
    for (unsigned n = 0; n < settings[9]; ++n)
      host += char(97 + (seedValue + n * 7) % 26);
    hostFail = settings[10];
    formatFail = settings[11];
    lookup = 0;
    trace.clear();
    std::string suffixes[] = {"", ".local", ".LOCAL", "x",
                              "." + std::string(30, 'a')};
    auto suffix = suffixes[settings[8]];
    state.suffix = suffix.c_str();
    seed(state.primaryText, seedValue + 3, 7);
    state.multiAddress = settings[0];
    state.suspended = settings[1];
    state.cacheValid = settings[2];
    state.changed = settings[3];
    state.refreshIntervalBits = settings[4];
    state.processCounterBits = settings[5];
    Presonus::UC::AdapterHandler handler(AdapterSourcePortTag{}, state);
    Presonus::UC::AdapterAddressList list(AdapterSourcePortTag{}, copied),
        otherList(AdapterSourcePortTag{}, other);
    Core::CStringBuffer<256> output, first;
    seed(output, seedValue, settings[13]);
    seed(first, seedValue, settings[13]);
    auto query = (host + suffix).substr(0, 255);
    std::string queries[] = {"",
                             query,
                             query,
                             ipText(eligible(snapshots[0], false)),
                             ipText(eligible(snapshots[1], true)),
                             "remote.invalid"};
    for (char &c : queries[2])
      if (c >= 'a' && c <= 'z')
        c -= 32;
    bool before = list.isEqual(otherList);
    list.copyFrom(settings[7] ? list : otherList);
    bool after = list.isEqual(otherList);
    list.toString(output);
    bool identity = handler.getAddressList(settings[6]) == &state.addresses;
    unsigned changedFirst = state.changed;
    handler.process();
    unsigned changedProcess = state.changed;
    auto counterProcess = state.processCounterBits;
    bool matches =
        handler.isLocalHostAddress_threadSafe(queries[settings[12]].c_str());
    handler.getFirstLocalHostAddress_threadSafe(first);
    handler.invalidateAddressList();
    identity &= handler.getAddressList(false) == &state.addresses;
    std::cout << hex(output.str(), 256) << '|' << hex(first.str(), 256) << '|'
              << before << ' ' << after << ' ' << matches << ' ' << identity
              << ' ' << changedFirst << ' ' << changedProcess << ' '
              << counterProcess << ' ' << unsigned(state.changed) << ' '
              << unsigned(state.cacheValid) << ' ' << state.processCounterBits
              << ' ' << state.storage.count << '|'
              << hex(state.storage.values.data(), 360) << '|'
              << hex(state.primaryText.str(), 256) << '|' << trace << '\n';
  }
}
