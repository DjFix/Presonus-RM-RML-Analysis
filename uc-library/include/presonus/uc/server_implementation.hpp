#pragma once

#include "presonus/uc/ClientSubscription.hpp"
#include "presonus/uc/event_dispatcher.hpp"
#include <memory>
#include <vector>

namespace presonus::uc {
struct ServerRosterAccess;
}

namespace Presonus::UC {
class ServerImplementation : public IEventHandler {
public:
  // Independent offline setup transfers ownership of initialized subscriptions.
  explicit ServerImplementation(
      std::vector<std::unique_ptr<ClientSubscription>> clients);
  ServerImplementation(const ServerImplementation &) = delete;
  ServerImplementation &operator=(const ServerImplementation &) = delete;
  virtual ~ServerImplementation();

  ClientSubscription *findClient(int identifier) const;
  bool hasClient(int identifier) const;
  bool hasClients() const;

private:
  Core::Vector<ClientSubscription *> clients_;
  friend struct presonus::uc::ServerRosterAccess;
};
} // namespace Presonus::UC
