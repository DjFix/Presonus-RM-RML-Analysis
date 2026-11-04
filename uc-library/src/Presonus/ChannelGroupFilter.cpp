#include "presonus/ChannelGroupFilter.hpp"
#include <algorithm>
#include <limits>
#include <stdexcept>

namespace Presonus {
ChannelGroupFilter::ChannelGroupFilter(int count) : visibility_(0, 5) {
  // Native negative counts and overflowing capacity rounding are outside the
  // bounded portable constructor domain.
  if (count < 0 || count > std::numeric_limits<int>::max() - 4)
    throw std::length_error("ChannelGroupFilter count");
  if (count <= visibility_.getCapacity() || visibility_.resize(count))
    visibility_.setCount(count);
  // The actual provider owns mutable bool[] storage; its public pointer view
  // is const-qualified. Native initializes the full capacity, including tail.
  auto *items = const_cast<bool *>(visibility_.getItems());
  if (items)
    std::fill_n(items, visibility_.getCapacity(), false);
}
void ChannelGroupFilter::setVisible(int index, bool visible) {
  // Preserve native negative-index writes to actual CCL ConstVector error.
  // An index at/above count leaves both storage and error unchanged.
  if (index < visibility_.count())
    visibility_.at(index) = visible;
}
} // namespace Presonus
