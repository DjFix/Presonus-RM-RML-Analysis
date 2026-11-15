#include "core/portable/coreparams.h"
#include "presonus/panel/MixerLCD.hpp"
#include <cstdlib>
#include <iostream>
#include <type_traits>
namespace presonus::panel::portable {
struct MixerLCDTestAccess {
  static Core::Portable::Parameter *
  parameter(const Presonus::Panel::MixerLCD &lcd) {
    return lcd.altKeyParameter_;
  }
  static const State *state(const Presonus::Panel::MixerLCD &lcd) {
    return &lcd.state_;
  }
};
} // namespace presonus::panel::portable
struct TrapBook final : presonus::panel::portable::Book {
  // Test boundary only: the setter must never execute a book operation.
  void command(unsigned) override { std::abort(); }
};
int main() {
  using Core::Portable::NumericParam;
  using Core::Portable::Parameter;
  static const Core::Portable::ParamInfo firstInfo =
      PARAM_FLOAT(1, "first", 0, 1, 0, .1f, 0, 0, 0, 0);
  static const Core::Portable::ParamInfo secondInfo =
      PARAM_FLOAT(2, "second", 0, 1, 0, .1f, 0, 0, 0, 0);
  NumericParam first(firstInfo, false), second(secondInfo, false);
  TrapBook book;
  presonus::panel::portable::State state{book};
  Presonus::Panel::MixerLCD lcd(state);
  using Access = presonus::panel::portable::MixerLCDTestAccess;
  static_assert(
      std::is_same_v<decltype(&Presonus::Panel::MixerLCD::setAltKeyParam),
                     void (Presonus::Panel::MixerLCD::*)(Parameter *)>);
  if (Access::parameter(lcd) != nullptr)
    return 2;
  unsigned index, choice;
  while (std::cin >> index >> choice) {
    if (choice > 2)
      return 3;
    Parameter *parameter = choice == 0   ? nullptr
                           : choice == 1 ? &first
                                         : &second;
    lcd.setAltKeyParam(parameter);
    if (Access::parameter(lcd) != parameter || Access::state(lcd) != &state ||
        &state.book != &book)
      return 4;
    unsigned observed = Access::parameter(lcd) == nullptr  ? 0
                        : Access::parameter(lcd) == &first ? 1
                                                           : 2;
    std::cout << index << ' ' << observed << " 1\n";
  }
  return 0;
}
