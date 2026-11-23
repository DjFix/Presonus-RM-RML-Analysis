#include "presonus/panel/Book.hpp"

#include <array>
#include <cstdlib>
#include <iostream>
#include <string_view>

using Presonus::Panel::Book;
using presonus::panel::BookInspector;
using presonus::panel::BorrowedBookState;
using Presonus::Panel::Page;

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const int index = std::atoi(argv[1]);
  const std::string_view kinds(argv[2]);
  if (kinds.size() > 32)
    return 2;
  std::array<std::array<unsigned char, 6>, 32> storage{};
  std::array<const unsigned char *, 32> pointers{};
  Page first, second;
  Book typed(0);
  for (std::size_t i = 0; i < kinds.size(); ++i) {
    const char kind = kinds[i];
    if (kind != '0') {
      storage[i][5] = kind != '1';
      pointers[i] = storage[i].data();
    }
    typed.add(kind == '2' ? &first : kind == '3' ? &second : nullptr);
  }
  const BorrowedBookState adapter(pointers.data(),
                                  static_cast<int>(kinds.size()));
  Book borrowed(adapter);
  BookInspector::setActivePosition(borrowed, index);
  BookInspector::setActivePosition(typed, index);
  const int legacyResult = borrowed.nextPage();
  const int typedResult = typed.nextPage();
  if (BookInspector::zero90(typed) != static_cast<std::uint32_t>(index) ||
      BookInspector::zero90(borrowed) != static_cast<std::uint32_t>(index))
    return 1;
  std::cout << legacyResult << ' ' << typedResult << '\n';
}
