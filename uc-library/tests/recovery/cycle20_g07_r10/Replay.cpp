#include "presonus/panel/Book.hpp"

#include <iostream>
#include <memory>

using Presonus::Panel::Book;
using Presonus::Panel::Page;

int main(int argc, char **argv) {
  if (argc < 3)
    return 2;
  const char *query = argv[1][0] == '1' ? argv[2] : nullptr;
  Book owned(0), borrowed(0);
  for (int i = 3; i < argc; ++i) {
    auto page = std::make_unique<Page>(Page::Elements{}, argv[i]);
    borrowed.add(page.get());
    if (!owned.addOwnedPage(page) || page)
      return 1;
  }
  std::cout << owned.hasPage(query) << ' ' << borrowed.hasPage(query) << '\n';
}
