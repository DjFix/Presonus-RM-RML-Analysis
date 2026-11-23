#include "presonus/panel/Book.hpp"

#include <iostream>
#include <string>

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;

  const int tag = std::stoi(argv[1]);
  const Presonus::Panel::Book owned(tag);
  const unsigned char slot[] = {0, 0, 0, 0, 0, 91};
  const unsigned char *slots[] = {slot};
  const presonus::panel::BorrowedBookState state(slots, 1);
  const Presonus::Panel::Book borrowed(state);
  using presonus::panel::BookInspector;
  if (!BookInspector::ownsStorage(owned) ||
      BookInspector::ownsStorage(borrowed) ||
      BookInspector::count(owned) != 0 || BookInspector::count(borrowed) != 1)
    return 3;

  std::cout << owned.getTag() << ' ' << borrowed.getTag() << '\n';
  return 0;
}
