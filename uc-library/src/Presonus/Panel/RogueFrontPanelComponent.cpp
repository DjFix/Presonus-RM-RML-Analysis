#include "presonus/panel/RogueFrontPanelComponent.hpp"
#include <cmath>
#include <cstring>
#include <stdexcept>
namespace Presonus::Rogue {
// Exact original internal data names and full payloads, including sentinels.
// RM13731 ELF 9320c53b...; range/section/hash records remain in native
// fixtures.
static_assert(sizeof(int) == 4);
static const int gChSelectTable[] = {
    0,  1,  2,  3,  4,  5,     6,     7,     8,     9,     10,    11,    12,
    13, 14, 15, 55, 56, 65527, 65527, 65527, 65527, 65527, 65527, 65527, -1};
static const int gChSelectOutTable[] = {32, 33, 34, 35, 36, 37, 51, 52,
                                        53, 54, 46, 47, 48, 49, 50, -1};
static const int gSoloTable[] = {
    0,     1,     2,     3,     4,     5,     6,     7,     8,
    9,     10,    11,    12,    13,    14,    15,    65527, 65527,
    65527, 65527, 65527, 65527, 65527, 65527, 65527, -1};
static const int gSoloOutTable[] = {32,    33,    34, 35, 36, 37, 65527, 65527,
                                    65527, 65527, 46, 47, 48, 49, 65527, -1};
static const int gChMuteTable[] = {
    0,     1,     2,     3,     4,     5,     6,     7,     8,
    9,     10,    11,    12,    13,    14,    15,    65527, 65527,
    65527, 65527, 65527, 65527, 65527, 65527, 65527, -1};
static const int gChMuteOutTable[] = {32, 33, 34, 35, 36, 37, 46,    47,
                                      48, 49, 50, 51, 52, 53, 65527, -1};
} // namespace Presonus::Rogue
namespace Presonus::Panel {
RogueFrontPanelComponent::~RogueFrontPanelComponent() = default;
bool RogueFrontPanelComponent::checkGeqViewRange() {
  if (!viewport_)
    throw std::logic_error("Rogue GEQ viewport binding required");
  std::int32_t selected = 0;
  if (viewport_->selected) {
    const float value = viewport_->selected->getValue();
    if (!std::isfinite(value) || value < -2147483648.f || value >= 2147483648.f)
      throw std::domain_error(
          "GEQ selection outside finite int32 source domain");
    selected = static_cast<std::int32_t>(value);
  }
  // Preserve native SUBS result bits and its BMI test without signed overflow.
  const std::uint32_t differenceBits =
      static_cast<std::uint32_t>(selected) -
      static_cast<std::uint32_t>(viewport_->offset);
  std::int32_t difference;
  std::memcpy(&difference, &differenceBits, sizeof(difference));
  if (difference >= 0 && difference < viewport_->mixer.inputChannels.count())
    return false;
  viewport_->offset = selected <= 15 ? 0 : 15;
  return true;
}
void RogueFrontPanelComponent::getTablesForGroup(int group, const int *&first,
                                                 const int *&second,
                                                 int &count) const {
  switch (group) {
  case 0:
    first = Rogue::gChSelectTable;
    second = Rogue::gChSelectOutTable;
    count = 13;
    break;
  case 1:
    first = Rogue::gSoloTable;
    second = Rogue::gSoloOutTable;
    count = 14;
    break;
  case 2:
    first = Rogue::gChMuteTable;
    second = Rogue::gChMuteOutTable;
    count = 18;
    break;
  default:
    break;
  }
}
} // namespace Presonus::Panel
