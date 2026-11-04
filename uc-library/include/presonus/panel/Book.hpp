#pragma once

#include "core/public/corevector.h"
#include <cstdint>

namespace presonus::panel {
// Independent source-port adapter. Borrowed slot pointers refer to at least six
// readable bytes; this borrowed adapter and Books using it do not own slots or
// their pointees. This is not an assertion about the original Book fields or
// inheritance.
struct BorrowedBookState {
  Core::ConstVector<const unsigned char *> slots;
  BorrowedBookState(const unsigned char *const *items, int count)
      : slots(items, count) {}
};
} // namespace presonus::panel

namespace presonus::panel {
struct BookInspector;
}

namespace Presonus::Panel {
class Book {
public:
  explicit Book(int initialValue);
  explicit Book(const presonus::panel::BorrowedBookState &state)
      : borrowedState_(&state) {}
  // Portable choice: preserves the full observed zero-extended byte. The
  // original C++ return declaration remains unresolved; no ARM ABI claim.
  std::uint32_t isValidPos(int position);

private:
  friend struct presonus::panel::BookInspector;
  // Independent source-port storage policy, not a recovered original layout.
  // The 32-slot capacity is a portable choice; only empty state is validated.
  Core::FixedSizeVector<const unsigned char *, 32> ownedSlots_;
  const presonus::panel::BorrowedBookState *borrowedState_ = nullptr;
  int initialValue_ = 0;
  std::uint32_t zeroState90_ = 0;
  std::uint32_t zeroState94_ = 0;
};
} // namespace Presonus::Panel

namespace presonus::panel {
// Independent inspection boundary for the bounded source-port state.
struct BookInspector {
  static int initialValue(const Presonus::Panel::Book &book) {
    return book.initialValue_;
  }
  static int count(const Presonus::Panel::Book &book) {
    return book.borrowedState_ ? book.borrowedState_->slots.count()
                               : book.ownedSlots_.count();
  }
  static bool ownsStorage(const Presonus::Panel::Book &book) {
    return !book.borrowedState_;
  }
  static const void *storage(const Presonus::Panel::Book &book) {
    return book.ownedSlots_.getItems();
  }
  static std::uint32_t zero90(const Presonus::Panel::Book &book) {
    return book.zeroState90_;
  }
  static std::uint32_t zero94(const Presonus::Panel::Book &book) {
    return book.zeroState94_;
  }
};
} // namespace presonus::panel
