#include "presonus/uc/udp_discovery.hpp"
#include <array>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <memory>
#include <string>
using namespace presonus::uc;
extern void discoveryControls(Presonus::UC::UDPDiscoveryHandler &,
                              Presonus::UC::IDiscoveryReplyHandler *);
extern void discoveryUpdate(Presonus::UC::UDPDiscoveryHandler &, void *,
                            const char *);
class BorrowedDiscoveryFixture final
    : public Presonus::UC::UDPDiscoveryHandler {
public:
  using UDPDiscoveryHandler::UDPDiscoveryHandler;
  bool registerServer(void *&, const Presonus::UC::DiscoveryDescriptor &,
                      int) override {
    std::abort();
  }
  void processDiscovery() override { std::abort(); }
  void onMulticastEvent(const char *, unsigned short, unsigned short, int,
                        Presonus::UC::EventItem *) override {
    std::abort();
  }
};
static std::string hex(const void *address, std::size_t length) {
  const auto *bytes = static_cast<const unsigned char *>(address);
  std::string output;
  const char digits[] = "0123456789abcdef";
  for (std::size_t n = 0; n < length; ++n) {
    output += digits[bytes[n] >> 4];
    output += digits[bytes[n] & 15];
  }
  return output;
}
static void pattern(char *output, unsigned seed, unsigned length,
                    unsigned capacity) {
  for (unsigned n = 0; n < capacity; ++n)
    output[n] = 33 + (seed + n * 7) % 90;
  output[length] = 0;
  output[capacity - 1] = 0;
}
static std::int32_t signedBits(std::uint32_t bits) {
  std::int32_t value;
  std::memcpy(&value, &bits, 4);
  return value;
}
int main() {
  std::uint64_t settings[16];
  while (std::cin >> settings[0]) {
    for (unsigned n = 1; n < 16; ++n)
      std::cin >> settings[n];
    unsigned count;
    std::cin >> count;
    if (count < 1 || count > 8)
      std::abort();
    std::array<DiscoveryEntryState, 8> values;
    std::array<std::unique_ptr<Presonus::UC::UDPDiscoveryEntry>, 8> entries;
    DiscoveryHandlerState state;
    BorrowedDiscoveryFixture handler(DiscoverySourcePortTag{}, state);
    if (handler.find(nullptr, settings[2], signedBits(settings[3])) ||
        handler.findLocal(signedBits(settings[3])))
      std::abort();
    for (unsigned n = 0; n < count; ++n) {
      unsigned flag0, dirty, flag3, port, hostlen, namelen;
      std::uint32_t identifier, version;
      std::cin >> flag0 >> dirty >> flag3 >> port >> identifier >> version >>
          hostlen >> namelen;
      auto &value = values[n];
      value.flag0 = flag0;
      value.dirty = dirty;
      value.flag3 = flag3;
      value.port = port;
      value.identifier = signedBits(identifier);
      value.versionWord = version;
      pattern(value.host.getBuffer(), settings[0] + n * 11, hostlen, 128);
      pattern(value.displayName.getBuffer(), settings[0] + n * 13 + 3, namelen,
              64);
      entries[n] = std::make_unique<Presonus::UC::UDPDiscoveryEntry>(
          DiscoverySourcePortTag{}, value);
      if (!state.entries.add(entries[n].get()))
        std::abort();
    }
    state.browsing = settings[13];
    state.counter28 = settings[14];
    state.counter2c = settings[15];
    char queryText[512], external[512];
    pattern(queryText, settings[0] + 7, settings[6], 512);
    pattern(external, settings[0] + 19, settings[10], 512);
    const char *query = settings[4] == 0   ? nullptr
                        : settings[4] == 1 ? queryText
                                           : values[settings[5]].host.str();
    const char *name =
        settings[7] == 0 ? nullptr
        : settings[7] == 1
            ? external
            : values[settings[7] == 2 || settings[7] == 3 ? settings[1]
                                                          : settings[8]]
                      .displayName.str() +
                  (settings[7] == 3 ? settings[9] : 0);
    auto identity = [&](Presonus::UC::UDPDiscoveryEntry *entry) {
      if (!entry)
        return 0U;
      for (unsigned n = 0; n < count; ++n)
        if (entries[n].get() == entry)
          return n + 1;
      std::abort();
    };
    handler.setConnection(reinterpret_cast<Presonus::UC::MulticastConnection *>(
        static_cast<std::uintptr_t>(settings[11])));
    discoveryControls(handler,
                      reinterpret_cast<Presonus::UC::IDiscoveryReplyHandler *>(
                          static_cast<std::uintptr_t>(settings[12])));
    if (state.browsing != 0)
      std::abort();
    unsigned remote = identity(
                 handler.find(query, settings[2], signedBits(settings[3]))),
             local = identity(handler.findLocal(signedBits(settings[3])));
    discoveryUpdate(handler, entries[settings[1]].get(), name);
    unsigned remoteafter = identity(
                 handler.find(query, settings[2], signedBits(settings[3]))),
             localafter = identity(handler.findLocal(signedBits(settings[3])));
    std::cout << "0 0 " << remote << ' ' << local << ' ' << remoteafter << ' '
              << localafter << ' '
              << reinterpret_cast<std::uintptr_t>(state.connection) << ' '
              << reinterpret_cast<std::uintptr_t>(state.reply) << ' '
              << unsigned(state.browsing) << ' ' << state.counter28 << ' '
              << state.counter2c;
    for (unsigned n = 0; n < count; ++n) {
      unsigned char flags[] = {values[n].flag0, 0x5a, values[n].dirty,
                               values[n].flag3};
      std::cout << '|' << hex(flags, 4) << ':' << values[n].versionWord << ':'
                << hex(values[n].displayName.str(), 64);
    }
    std::cout << '\n';
  }
}
