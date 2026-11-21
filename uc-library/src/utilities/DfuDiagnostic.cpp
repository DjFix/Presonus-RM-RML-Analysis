#include "presonus/utilities/dfu_diagnostic.hpp"

const char *getDFUErr(int code) {
  static constexpr const char *messages[] = {
      "Erase Sector", "Firmware Reset", "Transmit Packet",
      "Image Bad",    "Sequence Bad",   "DFU",
      "Timeout",      "Comm Error",     "Card not found",
      "Card reboot"};
  if (code < 2000 || code > 2009)
    return "DFU";
  return messages[code - 2000];
}
