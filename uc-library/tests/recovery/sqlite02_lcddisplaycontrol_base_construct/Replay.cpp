#include "presonus/panel/lcd_display_control.hpp"
#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include <cstdlib>
#include <iostream>

using Presonus::Panel::Control;
using presonus::panel::ControlAccess;
using Presonus::Panel::LCDDisplayControl;

namespace {
class Transport final : public Presonus::Panel::IPanelIO {
public:
  int open(const char *) override { std::abort(); }
  void close() override { std::abort(); }
  int enableHISpeed(bool) override { std::abort(); }
  int readMsg(Uart_Msg_Type &) override { std::abort(); }
  int writeMsg(Uart_Msg_Type &message) override {
    ++count;
    last = message;
    return 0;
  }
  unsigned count = 0;
  Uart_Msg_Type last{};
};

struct Derived final : LCDDisplayControl {
  Derived(int tag, unsigned index) : LCDDisplayControl(tag, index) {
    (void)index;
  }
};

void inspect(LCDDisplayControl &value) {
  std::cout << ControlAccess::tag(value) << ' '
            << ControlAccess::lastLevel(value) << ' '
            << (value.getParameter() == nullptr) << ' '
            << (value.getAltParameter() == nullptr) << ' '
            << (value.getTertiaryParameter() == nullptr) << ' '
            << (ControlAccess::io(value) == nullptr);
  std::cout << ' ' << (value.castTo(0x4c434443) == &value) << ' '
            << (value.castTo(0x4374726c) == &value);
  Transport transport;
  value.setIO(&transport);
  value.setValue(0x1234);
  std::cout << ' ' << transport.count;
  for (unsigned byte : transport.last.bytes)
    std::cout << ' ' << byte;
  std::cout << '\n';
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const int tag = std::stoi(argv[1]);
  const auto index = static_cast<unsigned>(std::stoul(argv[2]));
  (void)index;
  Derived value(tag, index);
  inspect(value);
}
