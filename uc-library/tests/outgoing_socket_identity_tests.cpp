#include "connection_fixture.hpp"
#include "presonus/uc/external_connection.hpp"
#include "presonus/uc/outgoing_connection.hpp"
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <type_traits>
static_assert(std::is_abstract_v<Presonus::UC::Connection>);
static_assert(std::is_abstract_v<Presonus::UC::SocketConnection>);
static_assert(std::is_abstract_v<Presonus::UC::OutgoingConnection>);
static_assert(std::is_abstract_v<Presonus::UC::ExternalConnection>);
static_assert(
    std::is_base_of_v<Presonus::UC::BasicConnection, Presonus::UC::Connection>);
static_assert(std::is_base_of_v<Presonus::UC::Connection,
                                Presonus::UC::SocketConnection>);
static_assert(std::is_base_of_v<Presonus::UC::SocketConnection,
                                Presonus::UC::OutgoingConnection>);
static_assert(std::is_base_of_v<Presonus::UC::Connection,
                                Presonus::UC::ExternalConnection>);
class CountedOutgoing final : public Presonus::UC::OutgoingConnection {
  int &calls_;

public:
  CountedOutgoing(presonus::uc::ConnectionState &state,
                  presonus::uc::BasicConnectionState &basic,
                  presonus::uc::SocketConnectionState &socket, int &calls)
      : OutgoingConnection(presonus::uc::SocketConnectionSourcePortTag{}, state,
                           basic, socket),
        calls_(calls) {}
  bool process(bool) override { std::abort(); }
  bool reset() override { std::abort(); }
  bool handleInternal(const Presonus::UC::Event &) override { std::abort(); }
  bool sendPeriodicEvent(const Presonus::UC::Event &) override { std::abort(); }
  int getType() const override {
    ++calls_;
    return OutgoingConnection::getType();
  }
};
class NonOutgoing final : public Presonus::UC::Connection {
  int kind_;
  int &calls_;

public:
  NonOutgoing(presonus::uc::ConnectionState &state,
              presonus::uc::BasicConnectionState &basic, int kind, int &calls)
      : Connection(state, basic), kind_(kind), calls_(calls) {}
  bool process(bool) override { std::abort(); }
  int getType() const override {
    ++calls_;
    return kind_;
  }
  void getAddress(const char *&address, unsigned short &port) const override {
    address = "test-nonoutgoing";
    port = 113;
  }
};
int main(int argc, char **argv) {
  std::ifstream fixture;
  if (argc == 2) {
    fixture.open(argv[1]);
    if (!fixture)
      return 2;
    std::cin.rdbuf(fixture.rdbuf());
  }
  unsigned present, kind, port;
  std::string text;
  while (std::cin >> present >> kind >> text >> port) {
    hierarchy_test::LiveBasicState basic;
    presonus::uc::ConnectionState state;
    presonus::uc::SocketConnectionState socket;
    socket.remoteAddress = text == "-" ? "" : text.c_str();
    socket.remotePort = static_cast<unsigned short>(port);
    int calls = 0;
    CountedOutgoing outgoing(state, basic.basic, socket, calls);
    NonOutgoing other(state, basic.basic, static_cast<int>(kind), calls);
    Presonus::UC::Connection *identity =
        kind == 1 ? static_cast<Presonus::UC::Connection *>(&outgoing)
                  : static_cast<Presonus::UC::Connection *>(&other);
    auto *cast =
        Presonus::UC::OutgoingConnection::cast(present ? identity : nullptr);
    if ((cast != nullptr) != (present && kind == 1))
      std::abort();
    const char *address = nullptr;
    unsigned short resultPort = 113;
    const Presonus::UC::Connection &dispatch = outgoing;
    dispatch.getAddress(address, resultPort);
    if (address != socket.remoteAddress.str() || resultPort != port ||
        dynamic_cast<const Presonus::UC::SocketConnection *>(&dispatch) !=
            &outgoing)
      std::abort();
    std::cout << (cast != nullptr) << ' ' << calls << ' '
              << outgoing.Presonus::UC::OutgoingConnection::getType() << ' '
              << (*address ? address : "-") << ' ' << resultPort << '\n';
  }
}
