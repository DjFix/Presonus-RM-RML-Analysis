#include "presonus/dice/manager.hpp"
#include <climits>

static_assert(CHAR_BIT == 8 && sizeof(int) == 4);

namespace Presonus::DICE {
std::int32_t Dice3Manager::setDiceRoutingProfile(Dice3RoutingProfile profile) {
  const auto word = static_cast<std::uint32_t>(profile);
  if (word == 1 || word == 2) {
    const std::uint32_t firstSource = word == 1 ? 0U : 2U;
    for (std::uint32_t sink = 0; sink < 4; ++sink)
      portableSink_->setRoute({1, sink, 1, firstSource + (sink & 1U)});
  } else if (word == 3) {
    portableSink_->setRoute({1, 0, 16, 0});
    portableSink_->setRoute({1, 1, 16, 1});
    portableSink_->setRoute({16, 0, 1, 0});
    portableSink_->setRoute({16, 1, 1, 1});
  }
  // Original code discards all individual route return values.
  return 0;
}
std::int32_t Dice3Manager::setDiceMonitorSource(int side, int sourceDevice,
                                                int source) {
  portableSink_->setRoute({1, side != 0 ? 1U : 0U,
                           static_cast<std::uint32_t>(sourceDevice) + 16U,
                           static_cast<std::uint32_t>(source)});
  return 0;
}
} // namespace Presonus::DICE
