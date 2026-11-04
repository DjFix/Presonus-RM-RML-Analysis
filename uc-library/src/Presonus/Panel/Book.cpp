#include "presonus/panel/Book.hpp"

namespace Presonus::Panel {
Book::Book(int initialValue) : initialValue_(initialValue) {}

std::uint32_t Book::isValidPos(int position) {
  const Core::ConstVector<const unsigned char *> &slots =
      borrowedState_ ? borrowedState_->slots : ownedSlots_;
  if (!slots.isValidIndex(position))
    return 0;
  const auto *slot = slots.at(position);
  return slot ? slot[5] : 0;
}
} // namespace Presonus::Panel
