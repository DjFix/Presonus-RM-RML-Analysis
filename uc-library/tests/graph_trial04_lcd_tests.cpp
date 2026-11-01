#include "presonus/panel/MixerLCD.hpp"
#include <iostream>
struct Recorder : presonus::panel::portable::Book {
  void command(unsigned slot) override { std::cout << slot << '\n'; }
};
int main() {
  Recorder book;
  presonus::panel::portable::State state{book};
  const Presonus::Panel::MixerLCD lcd(state);
  lcd.previous();
  lcd.next();
  lcd.up();
  lcd.down();
  lcd.store();
}
