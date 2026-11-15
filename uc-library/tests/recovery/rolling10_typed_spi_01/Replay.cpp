#include "presonus/panel/SPIControl.hpp"
#include "presonus/panel/protocol_comm.hpp"
#include <climits>
#include <iostream>
extern "C" void originalDefaultBroadcast() asm(
    "_ZN8Presonus5Panel8IPanelIO9broadcastEPNS0_7ControlE");
namespace {
Presonus::Panel::Control *activeControl = nullptr;
int providerCalls = 0, observedLevel = 0;

class DefaultIO final : public Presonus::Panel::IPanelIO {
public:
  int readMsg(Uart_Msg_Type &) override { throw "unreachable read"; }
  int writeMsg(Uart_Msg_Type &) override { throw "unreachable write"; }
  int open(const char *) override { throw "unreachable open"; }
  void close() override { throw "unreachable close"; }
  int enableHISpeed(bool) override { throw "unreachable speed"; }
};
} // namespace
extern "C" __attribute__((no_instrument_function)) void
__cyg_profile_func_enter(void *fn, void *) {
  if (fn == reinterpret_cast<void *>(&originalDefaultBroadcast) &&
      activeControl) {
    ++providerCalls;
    observedLevel = presonus::panel::ControlAccess::lastLevel(*activeControl);
  }
}
extern "C" __attribute__((no_instrument_function)) void
__cyg_profile_func_exit(void *, void *) {}
// Real inherited default provider remains the virtual target. No transport call
// is exercised; unknown hardware/derived broadcast behavior is outside domain.
int main() {
  int pairs[][2] = {{0, 0},
                    {0, 1},
                    {1, 0},
                    {-1, -1},
                    {-1, INT_MAX},
                    {INT_MAX, INT_MIN},
                    {INT_MIN, INT_MAX}};
  DefaultIO io;
  for (auto &pair : pairs)
    for (bool bound : {true, false}) {
      if (!bound && pair[0] != pair[1])
        continue;
      Presonus::Panel::SPIControl control(19);
      presonus::panel::ControlAccess::lastLevel(control) = pair[0];
      control.setIO(bound ? &io : nullptr);
      activeControl = &control;
      providerCalls = observedLevel = 0;
      control.broadcastValue(pair[1]);
      activeControl = nullptr;
      std::cout << presonus::panel::ControlAccess::lastLevel(control) << ' '
                << providerCalls << ' ' << observedLevel << '\n';
    }
  std::cout << io.broadcast(nullptr) << '\n';
}
