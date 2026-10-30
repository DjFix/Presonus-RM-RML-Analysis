#include "presonus/dice/uart_packet_log.hpp"
#include <iostream>

int main() {
  Presonus::DICE::SysexPacket packet;
  packet.bytes[0] = 0xf0;
  packet.bytes[1] = 1;
  packet.bytes[2] = 0xf7;
  presonus::dice::CclPacketLogSink sink;
  presonus::dice::CclAssemblyCallbacks callbacks(sink);
  callbacks.packetLog(packet);
  std::cout << "PASS actual CCL UART callback to recovered packet log sink\n";
}
