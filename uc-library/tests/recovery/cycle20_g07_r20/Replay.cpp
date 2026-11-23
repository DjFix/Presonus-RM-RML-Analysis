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
  const LCDComponent component;
  const std::unique_ptr<Book> first(component.createBook(tag));
  const std::unique_ptr<Book> second(component.createBook(tag));
  if (!first || !second || first.get() == second.get() ||
      first->getActivePage() || second->getActivePage() || component.getBook())
    return 1;
  std::cout << first->getTag() << ' ' << second->getTag() << '\n';
}
