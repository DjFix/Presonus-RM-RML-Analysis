#pragma once

#include "core/public/corevector.h"
#include <cstdint>

namespace presonus::panel {
// Independent source-port adapter. Borrowed slot pointers refer to at least six
// readable bytes; neither this adapter nor Book owns the slots or their
// pointees. This is not an assertion about the original Book fields or
// inheritance.
struct BorrowedBookState {
  Core::ConstVector<const unsigned char *> slots;
  BorrowedBookState(const unsigned char *const *items, int count)
      : slots(items, count) {}
};
} // namespace presonus::panel

namespace Presonus::Panel {
class Book {
public:
  explicit Book(const presonus::panel::BorrowedBookState &state)
      : state_(state) {}
  // Portable choice: preserves the full observed zero-extended byte. The
  // original C++ return declaration remains unresolved; no ARM ABI claim.
  std::uint32_t isValidPos(int position);

private:
  const presonus::panel::BorrowedBookState &state_;
};
} // namespace Presonus::Panel
