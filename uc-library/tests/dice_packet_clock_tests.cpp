#include "core/system/coretime.h"
#include "presonus/dice/sysex.hpp"
#include <array>
#include <iostream>
#include <stdexcept>

int main() {
  const unsigned char data[] = {0xf0, 0x11, 0xf7};
  const auto before = Core::SystemClock::getTime() / 1000000;
  const Presonus::DICE::SysexPacket packet(data, 3);
  const auto after = Core::SystemClock::getTime() / 1000000;
  const auto &metadata = packet.portableMetadata();
  if (packet.length != 3 || packet.bytes[0] != 0xf0 ||
      packet.bytes[1] != 0x11 || packet.bytes[2] != 0xf7 ||
      packet.bytes[254] != 0x45 || packet.bytes[255] != 0 ||
      metadata.constructedQuotient < before ||
      metadata.constructedQuotient > after ||
      metadata.headerWords != std::array<std::uint32_t, 2>{} ||
      metadata.trailingWords != std::array<std::uint32_t, 4>{})
    throw std::runtime_error("actual CCL packet clock/source composition");
  std::cout << "PASS actual CCL packet clock composition\n";
}
