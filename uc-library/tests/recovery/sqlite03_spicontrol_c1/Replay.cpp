#include "presonus/panel/SPIControl.hpp"
#include "presonus/panel/protocol_comm.hpp"
#include <array>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <vector>

namespace {
using Presonus::Panel::Control;
using presonus::panel::ControlAccess;
using Presonus::Panel::LEDControl;
using Presonus::Panel::SPIControl;
using presonus::surface_panel_port::LEDLifecycleAccess;
using presonus::surface_panel_port::LEDStateAccess;

struct InertIO final : Presonus::Panel::IPanelIO {
  explicit InertIO(Control &owner) : owner(owner) {}
  int readMsg(Uart_Msg_Type &) override { std::abort(); }
  int writeMsg(Uart_Msg_Type &) override { std::abort(); }
  int open(const char *) override { std::abort(); }
  void close() override { std::abort(); }
  int enableHISpeed(bool) override { std::abort(); }
  int broadcast(Control *current) override {
    if (current != &owner)
      std::abort();
    levels.push_back(ControlAccess::lastLevel(*current));
    return 0;
  }
  Control &owner;
  std::vector<int> levels;
};

struct DerivedSPI : SPIControl {
  DerivedSPI(int tag, int group, int match) : SPIControl(tag, group, match) {}
};

[[gnu::noipa]] void replay(SPIControl &spi) {
  LEDControl &led = spi;
  Control &control = led;
  if (control.castTo(0x4c656443) != &led ||
      control.castTo(0x4374726c) != &control)
    std::abort();
  const auto state = LEDStateAccess::state(led);
  const auto tag = ControlAccess::tag(control);
  const auto group = LEDLifecycleAccess::group(led);
  std::cout << tag << ' ' << group << ' ' << static_cast<std::int32_t>(state[3])
            << ' ' << ControlAccess::lastLevel(control) << ' '
            << (control.getParameter() != nullptr) << ' '
            << (control.getAltParameter() != nullptr) << ' '
            << (control.getTertiaryParameter() != nullptr) << ' '
            << (ControlAccess::io(control) != nullptr) << ' ' << state[1] << ' '
            << state[2] << ' ' << LEDLifecycleAccess::savedBlink(led) << ' '
            << state[4] << ' ' << LEDLifecycleAccess::on(led) << ' '
            << LEDLifecycleAccess::off(led);

  InertIO io(control);
  control.setIO(&io);
  for (int level : {-1, 22, 22, -5})
    control.broadcastValue(level);
  std::cout << ' ' << io.levels.size();
  for (int level : io.levels)
    std::cout << ' ' << level;
  std::cout << ' ' << ControlAccess::lastLevel(control) << '\n';
  control.setIO(nullptr);
}
} // namespace

int main() {
  constexpr int minimum = std::numeric_limits<int>::min();
  constexpr int maximum = std::numeric_limits<int>::max();
  constexpr std::array<std::array<int, 3>, 5> inputs = {
      {{4, 0, 0},
       {-5, 7, -1},
       {0, -1, 17},
       {minimum, maximum, -100},
       {maximum, minimum, 1}}};
  for (const auto &[tag, group, match] : inputs) {
#if SPI_CTOR_CASE == 1
    SPIControl value(tag, group, match);
#elif SPI_CTOR_CASE == 2
    DerivedSPI value(tag, group, match);
#else
#error "Select the sealed SPI constructor case"
#endif
    replay(value);
  }
  SPIControl compatible(4);
  replay(compatible);
}
