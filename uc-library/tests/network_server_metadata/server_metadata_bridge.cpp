#include "presonus/uc/server.hpp"
#include <array>
#include <cstdlib>
#include <iostream>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

int metadataTypeViaInterface(const Presonus::UC::Server &);
namespace {
void check(bool ok) {
  if (!ok)
    std::abort();
}
struct Spec {
  unsigned mode, a, b;
};
class ForeignServer final : public Presonus::UC::Server {
public:
  ForeignServer(presonus::uc::ServerSourcePortTag tag,
                presonus::uc::ServerState &state, std::uint32_t type)
      : Server(tag, state), type_(type) {}
  int getType() const override { return static_cast<int>(type_); }

private:
  std::uint32_t type_;
};
static_assert(std::is_trivially_destructible_v<Presonus::UC::LocalServer>);
static_assert(std::is_trivially_destructible_v<Presonus::UC::RemoteServer>);
static_assert(!std::has_virtual_destructor_v<Presonus::UC::Server>);
} // namespace

int main() {
  std::uint32_t seed;
  while (std::cin >> seed) {
    unsigned roundtrip, firstPort, secondPort;
    std::uint32_t flags, remoteFlags, word9, foreignType;
    std::array<Spec, 10> specs;
    std::cin >> roundtrip >> flags >> remoteFlags >> firstPort >> secondPort >>
        word9 >> foreignType;
    for (auto &spec : specs)
      std::cin >> spec.mode >> spec.a >> spec.b;
    check(std::cin && firstPort <= 65535 && secondPort <= 65535);
    presonus::uc::ServerState localState, foreignState;
    presonus::uc::RemoteServerState remoteState;
    std::array<std::pair<char *, std::size_t>, 10> buffers;
    for (unsigned n = 0; n < 4; ++n) {
      buffers[n] = {localState.strings[n].getBuffer(), 64};
      buffers[n + 4] = {remoteState.common.strings[n].getBuffer(), 64};
    }
    for (unsigned n = 0; n < 2; ++n)
      buffers[n + 8] = {remoteState.addresses[n].getBuffer(), 256};
    for (unsigned field = 0; field < buffers.size(); ++field) {
      auto [buffer, size] = buffers[field];
      for (unsigned n = 0; n < size; ++n)
        buffer[n] = static_cast<char>(33 + (n * 3 + seed + field * 13) % 90);
      buffer[(seed + field * 7) % (size - 1)] = 0;
      buffer[size - 1] = 0;
    }
    localState.flags = seed * 0x1020304U + 0x81020304U;
    localState.identifierBits = seed ^ 0x80123456U;
    remoteState.common.identifierBits = seed ^ 0xfedcba98U;
    const auto localID = localState.identifierBits;
    const auto remoteID = remoteState.common.identifierBits;
    const presonus::uc::ServerSourcePortTag tag;
    Presonus::UC::LocalServer local(tag, localState);
    Presonus::UC::RemoteServer remote(tag, remoteState);
    ForeignServer foreign(tag, foreignState, foreignType);
    Presonus::UC::ServerInfo info;
    const std::uint32_t marker = 0xaabb0000U + seed;
    info.originalDescriptorSize = marker;
    local.getInfo(info);
    check(info.originalDescriptorSize == marker);
    for (unsigned n = 0; n < 4; ++n)
      check(info.strings[n] == buffers[n].first);
    const auto initialInfoFlags = info.flags;
    Presonus::UC::DiscoveryDescriptor description;
    description.info.originalDescriptorSize = 0x66666666;
    description.addresses = {"descriptor-sentinel-0", "descriptor-sentinel-1"};
    const auto addressesBefore = description.addresses;
    description.ports = {0x6666, 0x6666};
    local.getDescription(description);
    check(description.info.originalDescriptorSize == 0x66666666 &&
          description.addresses == addressesBefore &&
          description.ports == std::array<std::uint16_t, 2>{0x6666, 0x6666} &&
          description.word9 == localID);
    for (unsigned n = 0; n < 4; ++n)
      check(description.info.strings[n] == buffers[n].first);
    const auto initialDescFlags = description.info.flags;
    std::array<std::vector<char>, 10> external;
    auto pointer = [&](unsigned field) -> const char * {
      const auto &spec = specs[field];
      if (spec.mode == 0)
        return nullptr;
      if (spec.mode == 1) {
        check(spec.a <= 1024);
        auto &text = external[field];
        text.resize(spec.a);
        for (unsigned n = 0; n < spec.a; ++n)
          text[n] = static_cast<char>(33 + (n * 7 + seed + field * 11) % 90);
        if (spec.b && spec.a)
          text[spec.a / 2] = 0;
        text.push_back(0);
        return text.data();
      }
      check(spec.mode == 2 && spec.a < buffers.size() &&
            spec.b < buffers[spec.a].second);
      return buffers[spec.a].first + spec.b;
    };
    Presonus::UC::ServerInfo input;
    for (unsigned n = 0; n < 4; ++n)
      input.strings[n] = pointer(n);
    input.flags = flags;
    local.setInfo(roundtrip ? info : input);
    for (unsigned n = 0; n < 4; ++n)
      check(info.strings[n] == buffers[n].first);
    Presonus::UC::DiscoveryDescriptor remoteInput;
    for (unsigned n = 0; n < 4; ++n)
      remoteInput.info.strings[n] = pointer(n + 4);
    for (unsigned n = 0; n < 2; ++n)
      remoteInput.addresses[n] = pointer(n + 8);
    remoteInput.info.flags = remoteFlags;
    remoteInput.ports = {static_cast<std::uint16_t>(firstPort),
                         static_cast<std::uint16_t>(secondPort)};
    remoteInput.word9 = word9;
    remote.setDescription(remoteInput);
    check(localState.identifierBits == localID &&
          remoteState.common.identifierBits == remoteID);
    const std::array<unsigned, 2> types{
        static_cast<unsigned>(metadataTypeViaInterface(local)),
        static_cast<unsigned>(metadataTypeViaInterface(remote))};
    auto normalize = [&](Presonus::UC::Server *server) -> unsigned {
      if (!server)
        return 0;
      if (server == &local)
        return 1;
      check(server == &remote);
      return 2;
    };
    std::array<Presonus::UC::Server *, 4> objects{nullptr, &local, &remote,
                                                  &foreign};
    std::array<unsigned, 8> casts;
    for (unsigned n = 0; n < objects.size(); ++n) {
      casts[n] = normalize(Presonus::UC::LocalServer::cast(objects[n]));
      casts[n + 4] = normalize(Presonus::UC::RemoteServer::cast(objects[n]));
    }
    constexpr char digits[] = "0123456789abcdef";
    std::string raw;
    raw.reserve(2048);
    for (auto [buffer, size] : buffers)
      for (unsigned n = 0; n < size; ++n) {
        const auto byte = static_cast<unsigned char>(buffer[n]);
        raw.push_back(digits[byte >> 4]);
        raw.push_back(digits[byte & 15]);
      }
    std::cout << raw << '|' << initialInfoFlags << ' ' << initialDescFlags
              << ' ' << marker << ' ' << localID << ' ' << localState.flags
              << ' ' << remoteState.common.flags << ' ' << remoteID << ' '
              << remoteState.ports[0] << ' ' << remoteState.ports[1] << ' '
              << remoteState.descriptorWord9;
    for (auto type : types)
      std::cout << ' ' << type;
    for (auto cast : casts)
      std::cout << ' ' << cast;
    std::cout << '\n';
  }
}
