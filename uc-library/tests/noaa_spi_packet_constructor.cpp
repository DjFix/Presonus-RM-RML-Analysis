#include "presonus/noaa/sysex_packet.hpp"
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
std::int64_t ticks[2];
unsigned calls;
} // namespace
namespace presonus::dice {
std::int64_t packetClockRawTicks() {
  if (calls >= 2)
    throw std::runtime_error("extra clock sample");
  return ticks[calls++];
}
} // namespace presonus::dice

int main() {
  unsigned count;
  if (!(std::cin >> count))
    return 2;
  for (unsigned index = 0; index < count; ++index) {
    unsigned size;
    std::string hex;
    if (!(std::cin >> size >> hex >> ticks[0] >> ticks[1]) || size > 255 ||
        hex.size() != 510)
      return 3;
    unsigned char data[255];
    for (unsigned i = 0; i < 255; ++i)
      data[i] = static_cast<unsigned char>(
          std::stoul(hex.substr(2 * i, 2), nullptr, 16));
    calls = 0;
    Presonus::NOAA::SysexPacket packet(data, static_cast<unsigned char>(size));
    const auto &m = packet.portableMetadata();
    std::cout << static_cast<unsigned>(packet.length) << ' ' << m.headerWords[0]
              << ' ' << m.headerWords[1] << ' ' << m.constructedQuotient;
    for (auto word : m.trailingWords)
      std::cout << ' ' << word;
    std::cout << ' ' << calls << ' ';
    const char *digits = "0123456789abcdef";
    for (unsigned i = 0; i < 255; ++i)
      std::cout << digits[packet.bytes[i] >> 4] << digits[packet.bytes[i] & 15];
    std::cout << '\n';
    // Original leaves byte255 untouched; portable value initialization is
    // deliberate and is tested separately from the ARM-equivalent domain.
    if (packet.bytes[255] != 0)
      return 4;
  }
}
