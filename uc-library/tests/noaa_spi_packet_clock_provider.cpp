#include "presonus/noaa/sysex_packet.hpp"
#include <iostream>

int main() {
  const unsigned char bytes[] = {0xf0, 1, 0xf7};
  const auto before = presonus::dice::packetClockRawTicks() / 1000000;
  Presonus::NOAA::SysexPacket packet(bytes, 3);
  const auto after = presonus::dice::packetClockRawTicks() / 1000000;
  if (packet.length != 3 || packet.bytes[0] != 0xf0 || packet.bytes[1] != 1 ||
      packet.bytes[2] != 0xf7 || packet.bytes[3] != 0x45 ||
      packet.portableMetadata().constructedQuotient < before ||
      packet.portableMetadata().constructedQuotient > after)
    return 1;
  std::cout << "PASS actual CCL clock provider constructor\n";
}
