#include "presonus/dice/sysex.hpp"
#include <cstring>

namespace Presonus::DICE {
const char *SysexPacket::getSysexCommandStr(unsigned char command) const {
  switch (command) {
  case 9:
    return "DRIVER PROG_SERIAL_COMMAND";
  case 30:
    return "SPI_NULL_CMD";
  case 1:
    return "INIT_COMMAND";
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
} // namespace Presonus::DICE
