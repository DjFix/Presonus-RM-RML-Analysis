#include "presonus/uc/network_manager_services.hpp"
#include "presonus/uc/report.hpp"
#include "presonus/uc/server.hpp"
#include <algorithm>
#include <cstring>
#include <stdexcept>

namespace {
Presonus::UC::ServerRegistrar &
registrar(presonus::uc::NetworkManagerState &state) {
  if (!state.registrar)
    throw std::invalid_argument("live source-backed registrar required");
  return *state.registrar;
}
void reportServer(const char *format, Presonus::UC::Server &server) {
  Presonus::UC::ServerInfo info;
  server.getInfo(info);
  UCReportMessage(0, format, info.strings[0]);
}
} // namespace

namespace Presonus::UC {
void NetworkManager::onRegistrationCompleted(void *context) {
  auto &owner = registrar(state_);
  auto *server = LocalServer::cast(owner.find(context, true));
  if (!server)
    return;
  reportServer("Server \"%s\" registration reply received.", *server);
  server->state_.localRegistrationByte = 0;
  owner.serverRegistered(server);
}

void NetworkManager::onServerChanged(void *context, const char *text) {
  auto &owner = registrar(state_);
  auto *server = owner.find(context, false);
  if (!server)
    return;
  reportServer("Server \"%s\" changed.", *server);
  if (auto *remote = RemoteServer::cast(server)) {
    auto &address = remote->remote_.addresses[1];
    auto *target = address.getBuffer();
    address.empty(); // Clear before strlen: same-start alias becomes empty.
    if (text) {
      const auto length = static_cast<std::uint32_t>(std::strlen(text));
      if (length != 0 && length <= 0x7fffffffU) {
        const auto count = std::min(length, std::uint32_t{255});
        // Defined source-port behavior for interior aliases. Original libc
        // strncpy overlap is outside the original differential domain.
        std::memmove(target, text, count);
        target[count] = 0;
      }
    }
  }
  owner.notifyServerChanged(server);
}
} // namespace Presonus::UC
