#include "presonus/panel/BeastPanelRegistrar.hpp"

namespace {
// Exact 32 words observed at 0x34fc54 in RM/RML mixer 13731. This
// private portable table does not claim the original data declaration.
constexpr std::int32_t tags[] = {20, 21, 22, 23, -1, -1, -1, -1, 12, 13, 14,
                                 15, 16, 17, 18, 19, 8,  9,  10, 11, -1, -1,
                                 -1, -1, 0,  1,  2,  3,  4,  5,  6,  7};
} // namespace

namespace Presonus::Panel {
const std::int32_t *BeastPanelRegistrar::getTags(int group, int &count) const {
  if (group != 20)
    return nullptr;
  count = 32;
  return tags;
}
} // namespace Presonus::Panel
