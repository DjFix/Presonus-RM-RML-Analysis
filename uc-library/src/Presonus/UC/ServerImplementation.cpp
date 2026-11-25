#include "presonus/uc/server_implementation.hpp"
#include <new>
#include <stdexcept>

namespace Presonus::UC {
ServerImplementation::ServerImplementation(
    std::vector<std::unique_ptr<ClientSubscription>> clients) {
  for (const auto &client : clients) {
    if (!client)
      throw std::invalid_argument(
          "A server roster requires live subscriptions");
    if (!clients_.add(client.get()))
      throw std::bad_alloc();
  }
  for (auto &client : clients)
    client.release();
}

ServerImplementation::~ServerImplementation() {
  for (int index = 0; index < clients_.count(); ++index)
    delete clients_.at(index);
}

ClientSubscription *ServerImplementation::findClient(int identifier) const {
  for (int index = 0; index < clients_.count(); ++index) {
    auto *client = clients_.at(index);
    if (client->sourcePortIdentifier() == identifier)
      return client;
  }
  return nullptr;
}

bool ServerImplementation::hasClient(int identifier) const {
  return findClient(identifier) != nullptr;
}

bool ServerImplementation::hasClients() const { return clients_.count() != 0; }
} // namespace Presonus::UC
