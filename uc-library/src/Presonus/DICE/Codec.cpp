#include "presonus/dice/codec.hpp"
#include <climits>

static_assert(CHAR_BIT == 8 && sizeof(unsigned int) == 4 &&
              sizeof(unsigned short) == 2);

unsigned int unpack32(const unsigned char *bytes) {
  // Nonfinal bytes are intentionally not masked: their high bits overlap the
  // adjacent field by OR, matching original decoding of noncanonical packets.
  return (static_cast<unsigned int>(bytes[0]) << 25) |
         (static_cast<unsigned int>(bytes[1]) << 18) |
         (static_cast<unsigned int>(bytes[2]) << 11) |
         (static_cast<unsigned int>(bytes[3]) << 4) | (bytes[4] & 15U);
}
unsigned short unpack16(const unsigned char *bytes) {
  return static_cast<unsigned short>(
      (static_cast<unsigned int>(bytes[0]) << 9) |
      (static_cast<unsigned int>(bytes[1]) << 2) | (bytes[2] & 3U));
}
void pack32(unsigned int value, unsigned char *bytes) {
  bytes[0] = static_cast<unsigned char>(value >> 25);
  bytes[1] = static_cast<unsigned char>((value >> 18) & 127U);
  bytes[2] = static_cast<unsigned char>((value >> 11) & 127U);
  bytes[4] = static_cast<unsigned char>(value & 15U);
  bytes[3] = static_cast<unsigned char>((value >> 4) & 127U);
}
void pack16(unsigned short value, unsigned char *bytes) {
  bytes[2] = static_cast<unsigned char>(value & 3U);
  bytes[0] = static_cast<unsigned char>(value >> 9);
  bytes[1] = static_cast<unsigned char>((value >> 2) & 127U);
}
