#include "presonus/panel/Book.hpp"
#include <array>
#include <climits>
#include <cstdint>
#include <iostream>

int main() {
  // Stream fixture rows from native ARM execution: count, index, null slot,
  // raw byte, expected r0. Also used by the focused CTest smoke mode.
  int count, index, nullSlot, byte;
  std::uint32_t expected;
  unsigned cases = 0;
  while (std::cin >> count >> index >> nullSlot >> byte >> expected) {
    std::array<unsigned char, 6> page{};
    page[5] = static_cast<unsigned char>(byte);
    const unsigned char *slots[] = {nullSlot ? nullptr : page.data()};
    presonus::panel::BorrowedBookState state(slots, count);
    Presonus::Panel::Book book(state);
    if (book.isValidPos(index) != expected)
      return 1;
    ++cases;
  }
  if (cases == 0) {
    std::array<unsigned char, 6> page{};
    const unsigned char *slots[] = {page.data(), nullptr};
    presonus::panel::BorrowedBookState state(slots, 2);
    Presonus::Panel::Book book(state);
    for (unsigned i = 0; i < 256; ++i) {
      page[5] = static_cast<unsigned char>(i);
      if (book.isValidPos(0) != i || book.isValidPos(1) != 0 ||
          book.isValidPos(-1) != 0 || book.isValidPos(INT_MIN) != 0 ||
          book.isValidPos(2) != 0 || book.isValidPos(INT_MAX) != 0)
        return 2;
    }
  }
  std::cout << "Book native fixture replay passed: " << cases << " rows\n";
}
