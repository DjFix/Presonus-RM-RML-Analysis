#include "presonus/dice/sysex.hpp"
#include <algorithm>
#include <cstring>

namespace Presonus::DICE {
SysexPacket::SysexPacket(const unsigned char *data, unsigned char size) {
  metadata_.headerWords = {0, 0};
  length = size;
  std::fill_n(bytes.begin(), 255, static_cast<unsigned char>(0x45));
  metadata_.constructedQuotient =
      presonus::dice::packetClockRawTicks() / 1000000;
  metadata_.trailingWords.fill(0);
  if (size != 0)
    std::memcpy(bytes.data(), data, size);
  metadata_.constructedQuotient =
      presonus::dice::packetClockRawTicks() / 1000000;
}
} // namespace Presonus::DICE
