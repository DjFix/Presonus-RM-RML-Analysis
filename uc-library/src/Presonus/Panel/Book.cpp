#include "presonus/panel/Book.hpp"

namespace Presonus::Panel {
std::uint32_t Book::isValidPos(int position) {
  if (!state_.slots.isValidIndex(position))
    return 0;
  const auto *slot = state_.slots.at(position);
  return slot ? slot[5] : 0;
}
} // namespace Presonus::Panel
