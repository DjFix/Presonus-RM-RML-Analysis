#include "presonus/panel/BeastFrontPanelComponent.hpp"
#include <cstdint>
namespace Presonus::Beast {
// Full original ELF data symbol _ZN8Presonus5BeastL14gChSelectTableE; SHA256
// ac0a2b0842f7e85a3e74f96937b2cf45c2fd77f56243a8a7433a6ce1a1eff0fa
static const int gChSelectTable[] = {
    0,  1,  2,     3,     4,     5,     6,     7,     8,     9,  10, 11,
    12, 13, 14,    15,    16,    17,    18,    19,    20,    21, 22, 23,
    55, 56, 65527, 65527, 65527, 65527, 65527, 65527, 65527, -1};
// Full original ELF data symbol _ZN8Presonus5BeastL17gChSelectOutTableE; SHA256
// 3eb689dfe9bb695d33f51a2a858e1181f88d99a90c698dbf6f4afbe34e180fca
static const int gChSelectOutTable[] = {32, 33, 34, 35, 36, 37, 38, 39, 40, 41,
                                        51, 52, 53, 54, 46, 47, 48, 49, 50, -1};
// Full original ELF data symbol _ZN8Presonus5BeastL10gSoloTableE; SHA256
// 4536dfdc60a688eb50f8293de90dad42d199aef17a3940eb6793315b810d5522
static const int gSoloTable[] = {
    0,     1,     2,     3,     4,     5,     6,     7,     8,     9,  10, 11,
    12,    13,    14,    15,    16,    17,    18,    19,    20,    21, 22, 23,
    65527, 65527, 65527, 65527, 65527, 65527, 65527, 65527, 65527, -1};
// Full original ELF data symbol _ZN8Presonus5BeastL13gSoloOutTableE; SHA256
// 01570ed9db5238cfe9f72b085b095158b6abeefbf197364918f7cb666a3c323a
static const int gSoloOutTable[] = {32, 33, 34, 35,    36,    37,    38,
                                    39, 40, 41, 65527, 65527, 65527, 65527,
                                    46, 47, 48, 49,    65527, -1};
// Full original ELF data symbol _ZN8Presonus5BeastL12gChMuteTableE; SHA256
// 4536dfdc60a688eb50f8293de90dad42d199aef17a3940eb6793315b810d5522
static const int gChMuteTable[] = {
    0,     1,     2,     3,     4,     5,     6,     7,     8,     9,  10, 11,
    12,    13,    14,    15,    16,    17,    18,    19,    20,    21, 22, 23,
    65527, 65527, 65527, 65527, 65527, 65527, 65527, 65527, 65527, -1};
// Full original ELF data symbol _ZN8Presonus5BeastL15gChMuteOutTableE; SHA256
// 333176ddd578225631d1dd84f3b280c1f23ad667be16a1e4cdfb784dd6406606
static const int gChMuteOutTable[] = {32, 33, 34, 35, 36,    37, 38,
                                      39, 40, 41, 46, 47,    48, 49,
                                      50, 51, 52, 53, 65527, -1};
} // namespace Presonus::Beast
namespace Presonus::Panel {
bool BeastFrontPanelComponent::checkGeqViewRange() {
  const int value = band ? static_cast<int>(band->getValue()) : 0;
  const auto difference = static_cast<std::int64_t>(value) - offset;
  if (difference >= 0 && difference < mixer.inputChannels.count())
    return false;
  offset = value <= 3 ? 0 : (value > 26 ? 7 : 4);
  return true;
}
void BeastFrontPanelComponent::getTablesForGroup(int group, const int *&first,
                                                 const int *&second,
                                                 int &count) const {
  switch (group) {
  case 0:
    first = Presonus::Beast::gChSelectTable;
    second = Presonus::Beast::gChSelectOutTable;
    count = 13;
    break;
  case 1:
    first = Presonus::Beast::gSoloTable;
    second = Presonus::Beast::gSoloOutTable;
    count = 14;
    break;
  case 2:
    first = Presonus::Beast::gChMuteTable;
    second = Presonus::Beast::gChMuteOutTable;
    count = 18;
    break;
  default:
    break;
  }
}
} // namespace Presonus::Panel
