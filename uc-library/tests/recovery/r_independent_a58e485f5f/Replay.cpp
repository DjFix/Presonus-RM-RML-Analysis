#include "presonus/uc/event_dispatcher.hpp"
#include "presonus/uc/server.hpp"
#include <array>
#include <cstdint>
#include <iostream>
#include <string>

namespace {
struct Handler final : Presonus::UC::IEventHandler {
  int handleEvent(void *, const Presonus::UC::Event &) override { return 0; }
};

struct Probe final : Presonus::UC::LocalServer {
  using LocalServer::LocalServer;
  unsigned registrationByte() const { return state_.localRegistrationByte; }
  bool ownsState() const { return ownedState_.get() == &state_; }
};
} // namespace

int main() {
  using namespace Presonus::UC;
  Handler handler;
  for (const int identifier : {0, 1, (-2147483647 - 1), -1}) {
    const auto id = static_cast<std::uint32_t>(identifier);
    for (auto *inputHandler : {static_cast<IEventHandler *>(nullptr),
                               static_cast<IEventHandler *>(&handler)}) {
      std::array<std::string, 4> values{"rack", "replay", "",
                                        std::string(80, 'x')};
      ServerInfo input;
      input.flags = id ^ 0x84620173u;
      for (std::size_t i = 0; i < values.size(); ++i)
        input.strings[i] = values[i].c_str();

      Probe probe(identifier, inputHandler, input);
      DiscoveryDescriptor output;
      output.addresses = {"first", "second"};
      output.ports = {4100, 4101};
      const auto addresses = output.addresses;
      const auto ports = output.ports;
      probe.getDescription(output);
      if (output.word9 != id || output.info.flags != input.flags ||
          probe.sourcePortHandler() != inputHandler || !probe.ownsState() ||
          probe.sourcePortStorage().count() != 0 ||
          LocalServer::cast(&probe) != &probe ||
          output.addresses != addresses || output.ports != ports)
        return 1;
      for (std::size_t i = 0; i < values.size(); ++i) {
        if (output.info.strings[i] == input.strings[i] ||
            output.info.strings[i] != values[i].substr(0, 63))
          return 2;
      }
      std::cout << output.word9 << ' ' << (inputHandler != nullptr) << ' '
                << probe.registrationByte() << '\n';
    }
  }
  LocalServer plain(19, &handler, ServerInfo{});
  DiscoveryDescriptor output;
  plain.getDescription(output);
  if (output.word9 != 19 || plain.sourcePortHandler() != &handler)
    return 3;
}
