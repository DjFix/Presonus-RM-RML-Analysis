#include "presonus/mixer/DelayComponent.hpp"
#include <cstring>

namespace Presonus::Mixer {
std::int32_t DelayComponent::mapIDs(int id) {
  switch (id) {
  case 2:
    return 1;
  case 11:
    return 2;
  case 12:
    return 3;
  case 13:
    return 4;
  case 14:
    return 5;
  case 15:
    return 6;
  case 16:
    return 7;
  default:
    return -1;
  }
}
const DelaySelectTypeMapEntry *DelayComponent::getSelectTypeMap() {
  // Native table 0x170470, 420 bytes, RM13731 ELF 9320c53b... . Values
  // preserve source bits; strings are relocated into this portable table.
  // Const pointer/row type are provisional; no original return-type claim.
  static const DelaySelectTypeMapEntry entries[] = {
      {0, 0, 0x1.0000000000000p+2f, 0x1.0000000000000p-1f, "delaytime"},
      {0, 1, 0x1.4000000000000p+2f, 0x1.0000000000000p-1f, "scaledtime"},
      {0, 2, 0x1.8000000000000p+2f, 0x1.0000000000000p-1f, "feedback"},
      {1, 0, 0x1.0000000000000p+2f, 0x1.0000000000000p-1f, "delaytime"},
      {1, 1, 0x1.4000000000000p+2f, 0x1.0000000000000p-1f, "scaledtime"},
      {1, 2, 0x1.8000000000000p+2f, 0x1.0000000000000p-1f, "feedback"},
      {1, 3, 0x1.c000000000000p+2f, 0x1.0000000000000p-1f, "filterfreq"},
      {1, 4, 0x1.0000000000000p+3f, 0x1.0000000000000p-1f, "filtergain"},
      {1, 5, 0x1.2000000000000p+3f, 0x1.0000000000000p-1f, "filterq"},
      {2, 0, 0x1.0000000000000p+2f, 0x1.0000000000000p-1f, "delaytime"},
      {2, 1, 0x1.4000000000000p+3f, 0x1.f5c2900000000p-2f, "scaledtime"},
      {2, 2, 0x1.6000000000000p+3f, 0x1.051eb80000000p-1f, "scaledtime"},
      {2, 3, 0x1.8000000000000p+3f, 0x1.0000000000000p-1f, "feedback"},
      {2, 4, 0x1.a000000000000p+3f, 0x1.0000000000000p-1f, "feedback"},
      {2, 5, 0x1.c000000000000p+3f, 0x1.0000000000000p-1f, "stereospread"},
      {3, 0, 0x1.0000000000000p+2f, 0x1.0000000000000p-1f, "delaytime"},
      {3, 1, 0x1.e000000000000p+3f, 0x1.6d91680000000p-2f, "scaledtime"},
      {3, 2, 0x1.0000000000000p+4f, 0x1.43126e0000000p-1f, "scaledtime"},
      {3, 3, 0x1.8000000000000p+2f, 0x1.0000000000000p-1f, "feedback"},
      {3, 4, 0x1.c000000000000p+3f, 0x1.0000000000000p-1f, "stereospread"},
      {-1, -1, -0x1.0000000000000p+0f, -0x1.0000000000000p+0f, ""},
  };
  return entries;
}
std::int32_t DelayComponent::getEffectTypeInternal(Presonus::EffectType type) {
  const std::uint32_t result = static_cast<std::uint32_t>(type) + 9U;
  std::int32_t signedResult;
  static_assert(sizeof(signedResult) == sizeof(result));
  // Preserve the original ARM addition's bits without signed overflow or an
  // implementation-defined unsigned-to-signed conversion.
  std::memcpy(&signedResult, &result, sizeof(result));
  return signedResult;
}
} // namespace Presonus::Mixer
