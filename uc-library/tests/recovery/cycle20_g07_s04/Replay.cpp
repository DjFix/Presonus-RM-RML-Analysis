#include "presonus/panel/Book.hpp"

#include <cstdlib>
#include <iostream>

using Presonus::Panel::Book;
using presonus::panel::BookInspector;
using Presonus::Panel::Page;

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const int count = std::atoi(argv[1]);
  if (count < 0 || count > 32)
    return 2;
  Page previous;
  Page inserted;
  Page *const value = argv[2][0] == '1' ? &inserted : nullptr;
  Book book(17);
  for (int index = 0; index < count; ++index)
    book.add(&previous);
  book.add(value);
  for (int index = 0; index < count; ++index)
    if (BookInspector::pageAt(book, index) != &previous)
      return 1;
  const int after = BookInspector::count(book);
  if (after > count && BookInspector::pageAt(book, count) != value)
    return 1;
  if (book.getTag() != 17 || !previous.isEnabled() || !inserted.isEnabled())
    return 1;
  std::cout << after << '\n';
}
