#include "presonus/dice/packet_logging.hpp"
#include "presonus/noaa/sysex_packet.hpp"
#include <cstring>

namespace Presonus::NOAA {
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

const char *SysexPacket::getSysexCommandStr(unsigned char command) const {
  switch (command) {
  case 1:
    return "INIT";
  case 2:
    return "IMG_START";
  case 3:
    return "IMG_PROGRAM";
  case 4:
    return "IMG_CONFIRM";
  case 5:
    return "IMG_FINISH";
  case 9:
    return "PROG_SERIAL";
  case 17:
    return "UI_SET";
  case 18:
    return "MUTE_START";
  case 19:
    return "MUTE_DONE";
  case 20:
    return "LINK_MODE";
  case 21:
    return "INTERCOM";
  case 22:
    return "ROUTE";
  case 23:
    return "STAT_REQ";
  case 24:
    return "STAT_RSP";
  case 25:
    return "CARD_REQ";
  case 26:
    return "CARD_RSP";
  case 27:
    return "DRIVER EVENT";
  case 28:
    return "GEQ_SETUP";
  case 29:
    return "GEQ";
  case 30:
    return "UCNETB";
  case 64:
    return "UCNET";
  default:
    static char err[32]{};
    err[0] = 0;
    std::memcpy(err, "UNKNOWN CHAR", 12);
    err[12] = 0;
    if (command != 0) {
      err[12] = static_cast<char>(command);
      err[13] = 0;
      err[31] = 0;
    }
    return err;
  }
}
} // namespace Presonus::NOAA
