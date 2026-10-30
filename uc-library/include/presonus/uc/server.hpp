#pragma once
#include "core/public/corestringbuffer.h"
#include "presonus/uc/server_registrar.hpp"
#include <array>
#include <cstdint>

namespace Presonus::UC {
// Independent value composition of measured descriptor values. This is not an
// original field declaration, object layout or ARM ABI assertion. word9 has no
// inferred semantic name: LocalServer exports its ID there; RemoteServer stores
// that same descriptor word separately and does not overwrite its common ID.
struct DiscoveryDescriptor {
  ServerInfo info{};
  std::array<const char *, 2> addresses{};
  std::array<std::uint16_t, 2> ports{};
  std::uint32_t word9 = 0;
};
} // namespace Presonus::UC
namespace presonus::uc {
struct ServerSourcePortTag {};
struct ServerState {
  std::array<Core::CStringBuffer<64>, 4> strings;
  std::uint32_t flags = 0;
  std::uint32_t identifierBits = 0;
  // Independent source-port storage for the callback-observed LocalServer
  // byte at original ARM +296. No original field name/layout/ctor claim.
  std::uint8_t localRegistrationByte = 0;
};
struct RemoteServerState {
  ServerState common;
  std::array<Core::CStringBuffer<256>, 2> addresses;
  std::array<std::uint16_t, 2> ports{};
  std::uint32_t descriptorWord9 = 0;
};
} // namespace presonus::uc
namespace Presonus::UC {
class LocalServer;
class RemoteServer;
// Partial source-port hierarchy. Original table: D1/D0/getType. Native table:
// getType only; no original lifecycle symbol or ARM vtable compatibility claim.
// A protected nonvirtual trivial lifetime avoids fabricating original D1/D0.
class Server {
public:
  virtual int getType() const = 0;
  void getInfo(ServerInfo &) const;
  void setInfo(const ServerInfo &);

protected:
  friend class NetworkManager;
  Server(presonus::uc::ServerSourcePortTag, presonus::uc::ServerState &state)
      : state_(state) {}
  ~Server() = default;
  presonus::uc::ServerState &state_;
};
class LocalServer : public Server {
public:
  LocalServer(presonus::uc::ServerSourcePortTag tag,
              presonus::uc::ServerState &state)
      : Server(tag, state) {}
  int getType() const override;
  static LocalServer *cast(Server *);
  void getDescription(DiscoveryDescriptor &) const;
};
class RemoteServer : public Server {
public:
  RemoteServer(presonus::uc::ServerSourcePortTag tag,
               presonus::uc::RemoteServerState &state)
      : Server(tag, state.common), remote_(state) {}
  int getType() const override;
  static RemoteServer *cast(Server *);
  void setDescription(const DiscoveryDescriptor &);

private:
  friend class NetworkManager;
  presonus::uc::RemoteServerState &remote_;
};
} // namespace Presonus::UC
