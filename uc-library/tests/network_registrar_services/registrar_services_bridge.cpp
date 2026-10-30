#include "presonus/uc/server_registrar.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>

namespace {
std::string trace;
constexpr std::array<const char *, 7> addresses{
    "", "alpha", "Alpha", "alpha.", "10.0.0.1", "10.0.0.10", "x"};
void check(bool ok) {
  if (!ok)
    std::abort();
}
int signedWord(std::uint32_t value) {
  int result;
  static_assert(sizeof(result) == sizeof(value));
  std::memcpy(&result, &value, sizeof(result));
  return result;
}
struct Listener final : Presonus::UC::INetworkListener {
  unsigned identifier = 0;
  void onServerAvailable(int id,
                         const Presonus::UC::ServerInfo &info) override {
    check(info.originalDescriptorSize == 24);
    trace += "A " + std::to_string(identifier) + " " +
             std::to_string(static_cast<std::uint32_t>(id)) + " " +
             std::to_string(info.flags) + " ";
    for (unsigned index = 0; index < 4; ++index) {
      check(info.strings[index] && info.strings[index][0] == 's');
      if (index)
        trace += ',';
      trace += info.strings[index] + 1;
    }
    trace += ';';
  }
  void onServerUnavailable(int id) override {
    trace += "R " + std::to_string(identifier) + " " +
             std::to_string(static_cast<std::uint32_t>(id)) + ";";
  }
  void onServerChanged(int id) override {
    trace += "C " + std::to_string(identifier) + " " +
             std::to_string(static_cast<std::uint32_t>(id)) + ";";
  }
};
} // namespace

int main() {
  std::uint32_t firstID;
  while (std::cin >> firstID) {
    trace.clear();
    trace.reserve(65536);
    std::array<presonus::uc::AvailableServerView, 6> views;
    std::array<std::array<std::string, 4>, 6> strings;
    std::array<std::uint64_t, 6> serverTokens{};
    std::array<std::uint64_t, 8> opaqueTokens{};
    auto opaque = [&](unsigned id) -> void * {
      check(id < opaqueTokens.size());
      return id ? &opaqueTokens[id] : nullptr;
    };
    presonus::uc::ServerRegistrarState state;
    for (unsigned n = 0; n < views.size(); ++n) {
      std::uint32_t id, flags, transport;
      unsigned context, handler, address, port, hidden;
      if (n == 0)
        id = firstID;
      else
        std::cin >> id;
      std::cin >> flags >> context >> handler >> address >> port >> transport >>
          hidden;
      check(address < addresses.size() && port <= 65535 && hidden <= 255);
      auto &view = views[n];
      view.identity =
          reinterpret_cast<Presonus::UC::Server *>(&serverTokens[n]);
      if (n < 3)
        view.localIdentity =
            reinterpret_cast<Presonus::UC::LocalServer *>(&serverTokens[n]);
      view.identifier = signedWord(id);
      view.flags = flags;
      view.handler =
          reinterpret_cast<Presonus::UC::IEventHandler *>(opaque(handler));
      view.registrationContext = opaque(context);
      view.remoteAddress = addresses[address];
      view.remotePort = static_cast<std::uint16_t>(port);
      view.remoteTransport = signedWord(transport);
      view.hidden = hidden != 0;
      for (unsigned k = 0; k < 4; ++k) {
        strings[n][k] = "s" + std::to_string(n * 4 + k);
        view.strings[k] = strings[n][k].c_str();
      }
      check(state.allServerViews.add(&view));
    }
    for (auto *items : {&state.localServers, &state.remoteServers}) {
      unsigned count;
      std::cin >> count;
      for (unsigned index = 0; index < count; ++index) {
        unsigned id;
        std::cin >> id;
        check(id >= 1 && id <= 6);
        check(items->add(&views[id - 1]));
      }
    }
    std::array<Listener, 6> listeners;
    for (unsigned n = 0; n < listeners.size(); ++n)
      listeners[n].identifier = n + 1;
    unsigned listenerCount;
    std::cin >> listenerCount;
    for (unsigned index = 0; index < listenerCount; ++index) {
      unsigned id;
      std::cin >> id;
      check(id >= 1 && id <= 6);
      check(state.listeners.add(&listeners[id - 1]));
    }
    unsigned handlerQuery, contextQuery, addressCode, portQuery, target,
        localTarget;
    std::uint32_t identifierQuery, transportQuery;
    std::cin >> handlerQuery >> contextQuery >> identifierQuery >>
        addressCode >> portQuery >> transportQuery >> target >> localTarget;
    check(addressCode <= addresses.size() && portQuery <= 65535 &&
          target >= 1 && target <= 6 && localTarget >= 1 && localTarget <= 3 &&
          std::cin);
    Presonus::UC::ServerRegistrar registrar(state);
    auto normalize = [&](Presonus::UC::Server *pointer) -> unsigned {
      if (!pointer)
        return 0;
      for (unsigned n = 0; n < views.size(); ++n)
        if (views[n].identity == pointer)
          return n + 1;
      std::abort();
    };
    std::array<unsigned, 7> results{
        normalize(
            registrar.find(reinterpret_cast<Presonus::UC::IEventHandler *>(
                opaque(handlerQuery)))),
        normalize(registrar.find(opaque(contextQuery), false)),
        normalize(registrar.find(opaque(contextQuery), true)),
        normalize(registrar.find(signedWord(identifierQuery), false)),
        normalize(registrar.find(signedWord(identifierQuery), true)),
        normalize(
            registrar.find(addressCode ? addresses[addressCode - 1] : nullptr,
                           static_cast<unsigned short>(portQuery),
                           signedWord(transportQuery))),
        registrar.hasLocalServers()};
    registrar.notifyServerAdded(views[target - 1].identity);
    registrar.notifyServerRemoved(views[target - 1].identity);
    registrar.notifyServerChanged(views[target - 1].identity);
    registrar.serverRegistered(views[localTarget - 1].localIdentity);
    for (unsigned n = 0; n < results.size(); ++n) {
      if (n)
        std::cout << ' ';
      std::cout << results[n];
    }
    std::cout << '|' << trace << '\n';
  }
}
