#include "presonus/panel/Book.hpp"

#include <cstdlib>
#include <iostream>
#include <string_view>

using Presonus::Panel::Book;
using presonus::panel::BookInspector;
using Presonus::Panel::Page;

int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  const int index = std::atoi(argv[1]);
  const std::string_view slots = argv[2];
  Page first, last, error;
  Book book(0);
  for (const char slot : slots) {
    if (slot == 'a')
      book.add(&first);
    else if (slot == 'b')
      book.add(&last);
    else if (slot == '-')
      book.add(nullptr);
    else
      return 2;
  }

  auto &fallback = Core::ConstVector<Page *>::getError();
  if (fallback)
    return 1;
  fallback = argv[3][0] == '1' ? &error : nullptr;
  BookInspector::setActivePosition(book, index);
  const Book &receiver = book;
  Page *const found = receiver.getActivePage();
  fallback = nullptr;

  if (found == &first)
    std::cout << 'a';
  else if (found == &last)
    std::cout << 'b';
  else if (found == &error)
    std::cout << 'e';
  else if (!found)
    std::cout << '-';
  else
    return 1;
  std::cout << '\n';
}
