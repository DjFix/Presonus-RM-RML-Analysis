#pragma once
#include "core/public/coreproperty.h"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
namespace Presonus::NOAA {
// Independent native source-port choice: actual Core::Property base plus an
// explicit byte payload. Original inheritance versus prefix composition and
// original field declarations remain unresolved; no ARM ABI claim follows.
struct NOAAStatusProperty : Core::Property {
  static constexpr Core::PropertyType kID = FOUR_CHAR_ID('s', 't', 'a', 't');
  explicit NOAAStatusProperty(const std::array<unsigned char, 52> &seed)
      : Core::Property(kID, sizeof(NOAAStatusProperty)), payload(seed) {}
  // ARM offsets are evidence labels for this independent projection, not native
  // object pointer arithmetic. Preserve seeded bytes not written by the method.
  void setWord(unsigned offset, std::uint32_t value) {
    assert(offset >= 8 && offset + 4 <= 60);
    std::memcpy(payload.data() + offset - 8, &value, 4);
  }
  void setByte(unsigned offset, unsigned char value) {
    assert(offset >= 8 && offset < 60);
    payload[offset - 8] = value;
  }
  std::array<unsigned char, 52> payload;
};
} // namespace Presonus::NOAA
