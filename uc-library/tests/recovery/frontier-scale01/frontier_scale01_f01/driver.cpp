#include "presonus/panel/Book.hpp"
#include <climits>
#include <cstring>
#include <iostream>
#include <new>
using presonus::panel::BookInspector;
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  auto bits = static_cast<std::uint32_t>(std::stoull(argv[1]));
  int value;
  static_assert(sizeof(value) == sizeof(bits));
  std::memcpy(&value, &bits, sizeof(value));
  Presonus::Panel::Book book(value);
  auto copied = book;
  bool distinct =
      BookInspector::storage(book) != BookInspector::storage(copied);
  std::cout << static_cast<std::uint32_t>(BookInspector::initialValue(book))
            << ' ' << BookInspector::count(book) << ' '
            << BookInspector::zero90(book) << ' ' << BookInspector::zero94(book)
            << ' ' << BookInspector::ownsStorage(book) << ' ' << distinct;
  for (int pos : {INT_MIN, -1, 0, 1, 31, 32, INT_MAX})
    std::cout << ' ' << book.isValidPos(pos);
  // Existing borrowed adapter: preserve dynamic state reference and full byte.
  unsigned char slot[6] = {0, 0, 0, 0, 0, 128};
  const unsigned char *items[] = {slot, nullptr};
  presonus::panel::BorrowedBookState state(items, 2);
  Presonus::Panel::Book borrowed(state);
  if (borrowed.isValidPos(0) != 128 || borrowed.isValidPos(1) != 0 ||
      borrowed.isValidPos(-1) != 0 || borrowed.isValidPos(2) != 0)
    return 3;
  slot[5] = 255;
  if (borrowed.isValidPos(0) != 255)
    return 4;
  state.slots = Core::ConstVector<const unsigned char *>(items, 0);
  if (borrowed.isValidPos(0) != 0)
    return 5;
  std::cout << "\n";
}
