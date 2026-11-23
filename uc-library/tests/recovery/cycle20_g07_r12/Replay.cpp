#include "presonus/panel/LCDComponent.hpp"

#include <cstdlib>
#include <iostream>
#include <memory>

using Presonus::Panel::Book;
using Presonus::Panel::LCDComponent;

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const int mode = std::atoi(argv[1]);
  Book first(1), other(2);
  LCDComponent component;
  Book *roster[] = {&other};
  component.bindBooks(LCDComponent::Books(roster, 1));
  if (mode)
    component.bindCurrentBook(&first);
  const LCDComponent &receiver = component;
  const Book *found = receiver.getBook();
  if (found && found != &first)
    return 1;
  std::cout << (found ? 1 : 0) << '\n';
}
