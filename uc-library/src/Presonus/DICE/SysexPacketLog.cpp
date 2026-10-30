#include "presonus/dice/packet_logging.hpp"
#include "presonus/dice/sysex.hpp"

namespace Presonus::DICE {
void SysexPacket::log() const {
  static const std::int64_t started =
      presonus::dice::packetClockRawTicks() / 1000000;
  presonus::dice::logPacket(
      bytes.data(), portableMetadata().trailingWords, started, this,
      [](const void *packet, unsigned char command) {
        return static_cast<const SysexPacket *>(packet)->getSysexCommandStr(
            command);
      });
}
} // namespace Presonus::DICE
