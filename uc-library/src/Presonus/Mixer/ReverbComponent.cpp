#include "presonus/mixer/ReverbComponent.hpp"
namespace Presonus::Mixer {
const ReverbSelectTypeMapEntry *ReverbComponent::getSelectTypeMap() {
  // Relocated RM13731 native table 0x170bfc, 480 bytes; ELF 9320c53b... .
  // Table and every string are independently hash-bound in native fixtures.
  static const ReverbSelectTypeMapEntry entries[] = {
      {0, 0, 0x1.0000000000000p+0f, 0x1.0000000000000p-1f, "decaytimeT1"},
      {1, 0, 0x1.0000000000000p+0f, 0x1.0000000000000p-1f, "decaytimeT2"},
      {1, 1, 0x1.0000000000000p+1f, 0x1.0000000000000p-1f, "predelayT2"},
      {1, 2, 0x1.8000000000000p+1f, 0x1.0000000000000p-1f, "earlyrefT2"},
      {2, 0, 0x1.0000000000000p+0f, 0x1.0000000000000p-1f, "decaytimeT3"},
      {2, 1, 0x1.0000000000000p+1f, 0x1.0000000000000p-1f, "predelayT3"},
      {2, 2, 0x1.8000000000000p+1f, 0x1.0000000000000p-1f, "earlyrefT3"},
      {3, 0, 0x1.0000000000000p+0f, 0x1.0000000000000p-1f, "decaytimeT4"},
      {3, 1, 0x1.0000000000000p+1f, 0x1.0000000000000p-1f, "predelayT4"},
      {3, 2, 0x1.8000000000000p+1f, 0x1.0000000000000p-1f, "earlyrefT4"},
      {4, 0, 0x1.0000000000000p+0f, 0x1.0000000000000p-1f, "decaytimeT5"},
      {4, 1, 0x1.0000000000000p+1f, 0x1.0000000000000p-1f, "predelayT5"},
      {4, 2, 0x1.8000000000000p+1f, 0x1.0000000000000p-1f, "earlyrefT5"},
      {5, 0, 0x1.0000000000000p+0f, 0x1.0000000000000p-1f, "decaytimeT6"},
      {5, 1, 0x1.0000000000000p+1f, 0x1.0000000000000p-1f, "predelayT6"},
      {5, 2, 0x1.8000000000000p+1f, 0x1.0000000000000p-1f, "earlyrefT6"},
      {6, 0, 0x1.0000000000000p+0f, 0x1.0000000000000p-1f, "decaytimeT7"},
      {6, 1, 0x1.0000000000000p+1f, 0x1.0000000000000p-1f, "predelayT7"},
      {7, 0, 0x1.0000000000000p+0f, 0x1.0000000000000p-1f, "decaytimeT8"},
      {7, 1, 0x1.0000000000000p+1f, 0x1.0000000000000p-1f, "predelayT8"},
      {7, 2, 0x1.8000000000000p+1f, 0x1.0000000000000p-1f, "earlyrefT8"},
      {8, 0, 0x1.0000000000000p+0f, 0x1.0000000000000p-1f, "decaytimeT9"},
      {8, 1, 0x1.0000000000000p+1f, 0x1.0000000000000p-1f, "predelayT9"},
      {-1, -1, -0x1.0000000000000p+0f, -0x1.0000000000000p+0f, ""},
  };
  return entries;
}
} // namespace Presonus::Mixer

namespace Presonus::Mixer {
int ReverbComponent::mapIDs(int selector) {
  // ARM subtracts two with wrapping arithmetic before its unsigned bound.
  const std::uint32_t index = static_cast<std::uint32_t>(selector) - 2u;
  static constexpr int mapping[] = {1,  -1, -1, -1, -1, -1, -1, -1,
                                    -1, 2,  3,  4,  5,  6,  7};
  return index <= 14u ? mapping[index] : -1;
}
} // namespace Presonus::Mixer
