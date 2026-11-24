#include "presonus/surface_panel/ControlHelpers.hpp"
#include <iostream>

namespace {
class CapturePort : public Presonus::IPanelPort {
public:
  int readMsg(Uart_Msg_Type &) override {
    ++reads;
    return 0;
  }

  int writeMsg(Uart_Msg_Type &message) override {
    ++writes;
    sameMessage = expected == &message;
    bytes = message.bytes;
    return 1;
  }

  const Uart_Msg_Type *expected = nullptr;
  std::array<std::uint8_t, 4> bytes{};
  bool sameMessage = false;
  int reads = 0;
  int writes = 0;
};

class Registrar : public Presonus::Panel::ControlRegistrar {
public:
  explicit Registrar(CapturePort &port) : port(port) {}

  void writeDualMsg(Uart_Msg_Type &message) override {
    ++dispatches;
    port.expected = &message;
    ControlRegistrar::writeDualMsg(message);
    port.expected = nullptr;
  }

  CapturePort &port;
  int dispatches = 0;
};
} // namespace

int main() {
  CapturePort port;
  Registrar registrar(port);
  registrar.bindPort(&port);
  registrar.scanFaders();
  if (registrar.dispatches != 1 || port.reads != 0 || port.writes != 1 ||
      !port.sameMessage || registrar.getPort() != &port)
    return 1;
  for (auto byte : port.bytes)
    std::cout << static_cast<unsigned>(byte) << ' ';
  std::cout << '\n';
  registrar.bindPort(nullptr);
  registrar.scanFaders();
  if (registrar.dispatches != 2 || port.reads != 0 || port.writes != 1 ||
      registrar.getPort() != nullptr)
    return 2;
  return 0;
}
