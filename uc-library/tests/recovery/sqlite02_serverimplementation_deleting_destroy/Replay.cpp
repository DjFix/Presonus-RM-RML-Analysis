#include "presonus/uc/server_implementation.hpp"
#include <array>
#include <cstdlib>
#include <iostream>
#include <string>

namespace presonus::uc {
struct ServerRosterAccess {
  static const auto &clients(const Presonus::UC::ServerImplementation &server) {
    return server.clients_;
  }
};
} // namespace presonus::uc

using Presonus::UC::ClientSubscription;
using Presonus::UC::ServerImplementation;
using presonus::uc::ServerRosterAccess;

namespace {
struct Allocation {
  const void *address = nullptr;
  const char *owner = nullptr;
  int identity = 0;
};
std::array<Allocation, 8> tracked;
std::array<Allocation, 8> released;
std::size_t releaseCount = 0;

Allocation observed(void *address) {
  if (address) {
    for (auto &allocation : tracked) {
      if (allocation.address == address) {
        auto result = allocation;
        allocation = {};
        return result;
      }
    }
  }
  return {};
}

void record(Allocation allocation) {
  if (allocation.owner && releaseCount < released.size())
    released[releaseCount++] = allocation;
}

class Receiver : public ServerImplementation {
public:
  using ServerImplementation::ServerImplementation;
  int handleEvent(void *, const Presonus::UC::Event &) override {
    std::abort(); // A roster-only check must never dispatch an event.
  }
};

void arm(const ServerImplementation &server, bool heapReceiver) {
  const auto &clients = ServerRosterAccess::clients(server);
  for (int i = 0; i < clients.count(); ++i)
    tracked[i] = {clients.at(i), "child", i + 1};
  if (clients.getItems())
    tracked[clients.count()] = {clients.getItems(), "vector", 0};
  if (heapReceiver)
    tracked[clients.count() + 1] = {&server, "receiver", 0};
}

[[gnu::noinline]] void destroyVirtually(ServerImplementation *server) {
  delete server;
}

struct SubobjectReceiver : public Receiver {
  using Receiver::Receiver;
};
} // namespace

extern "C" {
void __real__ZdlPv(void *);
void __real__ZdlPvm(void *, std::size_t);
void __real__ZdaPv(void *);
void __real__ZdaPvm(void *, std::size_t);

void __wrap__ZdlPv(void *pointer) {
  auto allocation = observed(pointer);
  __real__ZdlPv(pointer);
  record(allocation);
}
void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  auto allocation = observed(pointer);
  __real__ZdlPvm(pointer, size);
  record(allocation);
}
void __wrap__ZdaPv(void *pointer) {
  auto allocation = observed(pointer);
  __real__ZdaPv(pointer);
  record(allocation);
}
void __wrap__ZdaPvm(void *pointer, std::size_t size) {
  auto allocation = observed(pointer);
  __real__ZdaPvm(pointer, size);
  record(allocation);
}
}

int main(int argc, char **argv) {
  if (argc < 3 || argc > 8)
    return 1;
  const std::string mode = argv[1];
  const int query = std::stoi(argv[2]);
  std::vector<std::unique_ptr<ClientSubscription>> clients;
  std::array<ClientSubscription *, 5> identities{};
  for (int i = 3; i < argc; ++i) {
    clients.push_back(std::make_unique<ClientSubscription>(std::stoi(argv[i])));
    identities[i - 3] = clients.back().get();
  }
  if (mode == "deleting_destroy") {
    auto *server = new Receiver(std::move(clients));
    arm(*server, true);
    destroyVirtually(server);
  } else if (mode == "base_destroy") {
    SubobjectReceiver server(std::move(clients));
    arm(server, false);
  } else if (mode == "complete_destroy") {
    Receiver server(std::move(clients));
    arm(server, false);
  } else {
    Receiver server(std::move(clients));
    const auto &roster = ServerRosterAccess::clients(server);
    int result = 0;
    if (mode == "has_client")
      result = server.hasClient(query);
    else if (mode == "has_clients")
      result = server.hasClients();
    else if (mode == "find_client") {
      const auto *client = server.findClient(query);
      if (client) {
        for (int i = 0; i < argc - 3; ++i)
          if (identities[i] == client)
            result = i + 1;
        if (result == 0)
          return 2;
      }
    } else
      return 3;
    if (roster.count() != argc - 3)
      return 4;
    for (int i = 0; i < roster.count(); ++i) {
      if (roster.at(i) != identities[i] ||
          roster.at(i)->sourcePortIdentifier() != std::stoi(argv[i + 3]))
        return 5;
    }
    std::cout << result << '\n';
    return 0;
  }
  for (std::size_t i = 0; i < releaseCount; ++i)
    std::cout << released[i].owner << ' ' << released[i].identity << '\n';
}
