#include "presonus/dice/programmer.hpp"
#include <cassert>
#include <cstddef>

namespace Presonus::DICE {
std::int32_t Dice3Programmer::update() {
  // Caller must already have opened/bound the descriptor/runtime. Original
  // update does not call open/close and always erases exactly five sectors.
  assert(services_ != nullptr);
  for (int sector = 0; sector < 5; ++sector) {
    const float progress = static_cast<float>(sector) / 5.0f;
    printProgress("DICE3 Erase", progress, true);
    const auto result = eraseSector(sector);
    if (result != 0)
      return result;
  }
  printProgress("DICE3 Erase", 1.0f, false);
  const std::uint32_t remainder = state_.length & 255u;
  const std::uint32_t pages = (state_.length >> 8) + (remainder != 0 ? 1u : 0u);
  const int finalLength = remainder != 0 ? static_cast<int>(remainder) : 256;
  const float denominator = static_cast<float>(pages);
  for (std::uint32_t page = 0; page < pages; ++page) {
    const float progress = static_cast<float>(page) / denominator;
    const int length = page + 1 == pages ? finalLength : 256;
    printProgress("DICE3 Program:", progress, true);
    // Avoid the original unobserved post-last-page pointer advance. All
    // dereferenced page starts stay within the caller's valid image span.
    const auto *data = state_.image + static_cast<std::size_t>(page) * 256;
    if (writePage(static_cast<int>(page), data, length) != 0) {
      printProgress("DICE3 Programming Error", 0.0f, true);
      return -10;
    }
    const auto verification = verifyPage(static_cast<int>(page), data, length);
    if (verification != 0) {
      printProgress("DICE3 Verification Error", 0.0f, true);
      return verification;
    }
  }
  printProgress("DICE3 Programming complete", 1.0f, true);
  services_->sleepMilliseconds(500);
  return 0;
}
} // namespace Presonus::DICE
