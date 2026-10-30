#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <array>
#include <iostream>
#include <stdexcept>
#include <vector>
namespace {
void check(bool ok) {
  if (!ok)
    throw std::runtime_error("fader command mismatch");
}
class Port final : public Presonus::IPanelPort {
public:
  presonus::surface::PanelRegistrarCommandState &state;
  int mode, result;
  std::vector<std::array<std::uint8_t, 4>> frames;
  Port(presonus::surface::PanelRegistrarCommandState &s, int m, int r)
      : state(s), mode(m), result(r) {}
  int readMsg(Uart_Msg_Type &) override {
    throw std::logic_error("unexpected read boundary");
  }
  int writeMsg(Uart_Msg_Type &message) override {
    frames.push_back(message.bytes);
    if (mode == 2)
      state.port = nullptr;
    if (mode == 3)
      message.bytes.fill(0xff);
    return result;
  }
};
} // namespace
int main() {
  unsigned cases = 0;
  for (int operation = 0; operation != 3; ++operation)
    for (int value = 0; value != (operation == 0   ? 256
                                  : operation == 1 ? 1
                                                   : 2);
         ++value)
      for (int mode = 0; mode != 4; ++mode)
        for (int result : {-7, 0, 9}) {
          presonus::surface::PanelRegistrarCommandState state;
          Port port(state, mode, result);
          state.port = mode == 1 ? nullptr : &port;
          Presonus::Surface::PanelRegistrar registrar(state);
          std::vector<unsigned char> commands;
          if (operation == 0) {
            registrar.sendFaderFunctionMessage(
                static_cast<unsigned char>(value));
            commands.push_back(static_cast<unsigned char>(value));
          } else if (operation == 1) {
            registrar.requestUpdatedFaderParameters();
            commands = {1, 2};
          } else {
            registrar.invokeFaderCalibration(value != 0);
            if (value)
              commands = {0};
          }
          std::vector<std::array<std::uint8_t, 4>> expected;
          for (std::size_t i = 0; i < commands.size(); ++i)
            if (mode != 1 && !(mode == 2 && i > 0))
              expected.push_back({0x67, 0x0e, commands[i], 0});
          check(port.frames == expected);
          ++cases;
        }
  check(cases == 3108);
  // Pure original mapping helpers still permit independent default
  // construction.
  Presonus::Surface::PanelRegistrar unbound;
  unbound.invokeFaderCalibration(false);
  std::cout << "fader commands 3108 PASS\n";
}
