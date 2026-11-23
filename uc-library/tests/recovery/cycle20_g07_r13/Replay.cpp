#include "presonus/panel/LCDComponent.hpp"

#include <cstdlib>
#include <iostream>
#include <memory>

using Presonus::Panel::Book;
using Presonus::Panel::LCDComponent;

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const int tag = std::atoi(argv[1]);
  Book first(1), second(2), duplicate(1);
  Book *books[] = {&first, &second, &duplicate};
  LCDComponent component;
  component.bindCurrentBook(&duplicate);
  component.bindBooks(LCDComponent::Books(books, tag ? 3 : 0));
  const LCDComponent &receiver = component;
  const Book *found = receiver.getBook(tag);
  if (found && found != &first && found != &second)
    return 1;
  std::cout << (found == &first ? 1 : found == &second ? 2 : 0) << '\n';
}
