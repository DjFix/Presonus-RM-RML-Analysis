#include "fixture_manager.hpp"
#include "presonus/uc/ccl_bindings.hpp"
#include "presonus/uc/server.hpp"
#include "presonus/uc/server_registrar.hpp"
#include <cassert>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>
using namespace Presonus::UC;
namespace {
std::vector<std::string> calls;
std::string words(const Event &e) {
  return std::to_string(e.type) + "," + std::to_string(e.reserved04) + "," +
         std::to_string(e.routeA) + "," + std::to_string(e.routeB);
}
struct Item final : EventItem {
  MessageEvent message;
  bool input = false;
  Event &getData() override {
    if (input)
      calls.push_back("get");
    return message.header;
  }
};
struct Provider {
  presonus::uc::CclFactoryRegistry registry;
  EventFactory factory{registry.registry()};
  presonus::uc::FactoryCodec codec{};
  int outcome, count = 0, failAt;
  Provider(int value, int targetCount)
      : outcome(value), failAt(targetCount == 3 ? 2 : 1) {
    codec.context = this;
    codec.clone = [](void *context, const Event &event) -> EventItem * {
      auto &self = *static_cast<Provider *>(context);
      ++self.count;
      if (self.outcome == 2 && self.count == self.failAt)
        throw std::runtime_error("explicit fixture clone failure");
      if (self.outcome == 1)
        return nullptr;
      auto *item = new Item;
      item->message.header = event;
      return item;
    };
    codec.create = [](void *) -> EventItem * { return new Item; };
    codec.write = [](void *, BufferWriter &writer, const Event &event) {
      return EventClass{}.write(writer, event);
    };
    codec.read = [](void *, EventItem *item, BufferReader &reader) {
      return item && EventClass{}.read(item->getData(), reader);
    };
    codec.destroy = [](void *, EventItem *item) { delete item; };
    registry.registry().fallback = &codec;
  }
};
} // namespace
extern "C" Server *
__real__ZNK8Presonus2UC15ServerRegistrar4findEib(const ServerRegistrar *, int,
                                                 bool);
extern "C" Server *
__wrap__ZNK8Presonus2UC15ServerRegistrar4findEib(const ServerRegistrar *self,
                                                 int identifier, bool local) {
  assert(local);
  calls.push_back("find-local," +
                  std::to_string(static_cast<std::uint32_t>(identifier)));
  return __real__ZNK8Presonus2UC15ServerRegistrar4findEib(self, identifier,
                                                          local);
}
extern "C" Server *__real__ZNK8Presonus2UC15ServerRegistrar4findEPKcti(
    const ServerRegistrar *, const char *, unsigned short, int);
extern "C" Server *__wrap__ZNK8Presonus2UC15ServerRegistrar4findEPKcti(
    const ServerRegistrar *self, const char *address, unsigned short port,
    int transport) {
  assert(std::strcmp(address, "10.1.2.3") == 0);
  calls.push_back("find-remote," + std::to_string(port) + "," +
                  std::to_string(static_cast<std::uint32_t>(transport)));
  return __real__ZNK8Presonus2UC15ServerRegistrar4findEPKcti(self, address,
                                                             port, transport);
}
extern "C" int __real__ZN8Presonus2UC14NetworkManager9sendEventERKNS0_5EventEi(
    NetworkManager *, const Event &, int);
extern "C" int __wrap__ZN8Presonus2UC14NetworkManager9sendEventERKNS0_5EventEi(
    NetworkManager *self, const Event &event, int flags) {
  assert(flags == 0);
  calls.push_back("send," + words(event));
  return __real__ZN8Presonus2UC14NetworkManager9sendEventERKNS0_5EventEi(
      self, event, flags);
}
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream input(argv[1]);
  assert(input);
  unsigned cases = 0;
  std::uint32_t tag, source, target, serverID;
  int transport, firstPort, secondPort, found, targetCount, outcome;
  while (input >> tag >> transport >> firstPort >> secondPort >> found >>
         targetCount >> source >> target >> serverID >> outcome) {
    Core::Vector<int> dispatchIDs;
    for (int i = 0, value; i < targetCount; ++i) {
      input >> value;
      dispatchIDs.add(value);
    }
    std::string expectedTrace;
    input >> expectedTrace;
    assert(input);
    Provider provider(outcome, targetCount);
    presonus::uc::EventDispatcherState dispatcherState;
    EventDispatcher dispatcher(dispatcherState);
    presonus::uc::ServerState common;
    common.identifierBits = serverID;
    LocalServer local(presonus::uc::ServerSourcePortTag{}, common);
    presonus::uc::RemoteServerState remoteState;
    remoteState.common.identifierBits = serverID;
    RemoteServer remote(presonus::uc::ServerSourcePortTag{}, remoteState);
    Server *server = transport == 0 ? static_cast<Server *>(&local)
                                    : static_cast<Server *>(&remote);
    presonus::uc::AvailableServerView registered;
    registered.identity = server;
    std::memcpy(&registered.identifier, &source, 4);
    registered.remoteAddress = "10.1.2.3";
    registered.remotePort = static_cast<unsigned short>(firstPort);
    std::memcpy(&registered.remoteTransport, &source, 4);
    presonus::uc::ServerRegistrarState registrarState;
    if (found) {
      (transport == 0 ? registrarState.localServers
                      : registrarState.remoteServers)
          .add(&registered);
      registrarState.allServerViews.add(&registered);
    }
    ServerRegistrar registrar(registrarState);
    presonus::uc::MulticastServerView multicast{
        server, transport == 0 ? &common : &remoteState.common, &dispatchIDs};
    presonus::uc::NetworkManagerState state{dispatcher, provider.factory};
    state.registrar = &registrar;
    state.multicastServers.add(&multicast);
    state.messageView = [](void *, const Event &event) -> const MessageEvent & {
      return *reinterpret_cast<const MessageEvent *>(&event);
    };
    state.storeFlags = [](void *, EventItem &, int flags) {
      assert(flags == 0);
    };
    FixtureManager manager(state);
    Item item;
    item.input = true;
    item.message.header = {tag, 16, source, target};
    calls.clear();
    bool threw = false;
    try {
      manager.onMulticastEvent(
          "10.1.2.3", static_cast<unsigned short>(firstPort),
          static_cast<unsigned short>(secondPort), transport, &item);
    } catch (const std::runtime_error &e) {
      assert(std::strcmp(e.what(), "explicit fixture clone failure") == 0);
      threw = true;
      calls.push_back(
          "cleanup"); // Actual caught exception and restored data below.
    }
    assert(item.message.header.type == tag &&
           item.message.header.reserved04 == 16 &&
           item.message.header.routeA == source &&
           item.message.header.routeB == target);
    std::string trace;
    for (const auto &call : calls)
      trace += call + ";";
    assert(trace == expectedTrace);
    unsigned queued = 0;
    while (auto *owned = dispatcherState.retrieve()) {
      const Event &event = owned->getData();
      assert(event.type == tag && event.routeA == serverID);
      assert(event.routeB ==
             static_cast<std::uint32_t>(dispatchIDs.at(queued)));
      delete owned;
      ++queued;
    }
    assert(queued == static_cast<unsigned>(outcome == 0 ? provider.count
                                           : threw      ? provider.count - 1
                                                        : 0));
    ++cases;
  }
  std::cout << "{\"passed\":true,\"cases\":" << cases << "}\n";
}
