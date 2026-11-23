#include "presonus/panel/Book.hpp"

#include <iostream>
#include <string>
#include <tuple>

using Presonus::Panel::Book;
using presonus::panel::BookInspector;

static auto state(Book &book) {
  return std::make_tuple(
      BookInspector::initialValue(book), BookInspector::count(book),
      BookInspector::ownsStorage(book), BookInspector::storage(book),
      BookInspector::zero90(book), BookInspector::zero94(book),
      book.isValidPos(-1), book.isValidPos(0), book.isValidPos(1),
      book.isValidPos(2));
}

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;

  Book owned(std::stoi(argv[1]));
  unsigned char first[] = {
      4, 3, 2, 1, 0, static_cast<unsigned char>(std::stoi(argv[2]))};
  const unsigned char second[] = {0, 1, 2, 3, 4, 0xee};
  const unsigned char *slots[] = {first, second};
  const presonus::panel::BorrowedBookState borrowedState(slots, 2);
  Book borrowed(borrowedState);
  const auto ownedBefore = state(owned);
  const auto borrowedBefore = state(borrowed);
  if (borrowed.isValidPos(0) != first[5] ||
      borrowed.isValidPos(1) != second[5] ||
      BookInspector::count(borrowed) != 2 || BookInspector::count(owned) != 0)
    return 3;

  using Toggle = void (Book::*)();
  constexpr Toggle directEntry = &Book::togglePage;
  (owned.*directEntry)();
  (borrowed.*directEntry)();
  const bool unchanged =
      state(owned) == ownedBefore && state(borrowed) == borrowedBefore &&
      borrowedState.slots.at(0) == first && borrowedState.slots.at(1) == second;
  ++first[5];
  if (borrowed.isValidPos(0) != first[5])
    return 4;

  std::cout << unchanged << '\n';
  return 0;
}
