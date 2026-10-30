#include "presonus/uc/server.hpp"
#include <algorithm>
#include <cstring>

namespace presonus::uc {
// App-specific alias adaptation. The pinned CCL assignment uses strncpy and is
// undefined for an interior source pointer; retain it for ordinary/same-start
// assignment and use defined memmove only for interior aliases. Clear before
// measuring length, preserving the firmware's self-alias and untouched tails.
template <int Size>
static void assignServerString(Core::CStringBuffer<Size> &target,
                               const char *source) {
  auto *buffer = target.getBuffer();
  const auto sourceAddress = reinterpret_cast<std::uintptr_t>(source);
  const auto start = reinterpret_cast<std::uintptr_t>(buffer);
  if (sourceAddress > start && sourceAddress < start + Size) {
    target.empty();
    const auto count =
        std::min(std::strlen(source), static_cast<std::size_t>(Size - 1));
    std::memmove(buffer, source, count);
    buffer[count] = 0;
  } else {
    target = source;
  }
}
} // namespace presonus::uc

namespace Presonus::UC {
void Server::getInfo(ServerInfo &info) const {
  for (unsigned index = 0; index < state_.strings.size(); ++index)
    info.strings[index] = state_.strings[index].str();
  info.flags = state_.flags;
}

void Server::setInfo(const ServerInfo &info) {
  for (unsigned index = 0; index < state_.strings.size(); ++index)
    presonus::uc::assignServerString(state_.strings[index],
                                     info.strings[index]);
  state_.flags = info.flags;
}

int LocalServer::getType() const { return 0; }

LocalServer *LocalServer::cast(Server *server) {
  return server && server->getType() == 0 ? static_cast<LocalServer *>(server)
                                          : nullptr;
}

void LocalServer::getDescription(DiscoveryDescriptor &description) const {
  description.word9 = state_.identifierBits;
  getInfo(description.info);
}

int RemoteServer::getType() const { return 1; }

RemoteServer *RemoteServer::cast(Server *server) {
  return server && server->getType() == 1 ? static_cast<RemoteServer *>(server)
                                          : nullptr;
}

void RemoteServer::setDescription(const DiscoveryDescriptor &description) {
  for (unsigned index = 0; index < remote_.addresses.size(); ++index)
    presonus::uc::assignServerString(remote_.addresses[index],
                                     description.addresses[index]);
  remote_.ports = description.ports;
  remote_.descriptorWord9 = description.word9;
  setInfo(description.info);
}
} // namespace Presonus::UC
