#include "core/public/corestringbuffer.h"
#include "core/system/coredebug.h"
#include "presonus/noaa/card.hpp"
#include "presonus/noaa/status_property.hpp"
#include <cstdio>
#include <cstring>
namespace {
std::uint32_t word(const Presonus::NOAA::NOAAStatusProperty &p,
                   unsigned offset) {
  std::uint32_t value;
  std::memcpy(&value, p.payload.data() + offset - 8, 4);
  return value;
}
int signedWord(std::uint32_t bits) {
  static_assert(sizeof(int) == 4);
  int value;
  std::memcpy(&value, &bits, 4);
  return value;
}
} // namespace
namespace Presonus::NOAA {
unsigned int TCard::generateAlternateMac(unsigned int serial) {
  Core::CStringBuffer<32> decimal(nullptr), chunk(nullptr), combined(nullptr);
  decimal.appendFormat("%08u", serial);
  unsigned int first = 0, second = 0, third = 0, result = 0;
  decimal.subString(chunk, 0, 2);
  std::sscanf(chunk.str(), "%u", &first);
  decimal.subString(chunk, 2, 2);
  std::sscanf(chunk.str(), "%u", &second);
  decimal.subString(chunk, 4, 4);
  std::sscanf(chunk.str(), "%u", &third);
  first += 30;
  combined.appendFormat("%02d%02d%04d", int(second), int(first), int(third));
  std::sscanf(combined.str(), "%08u", &result);
  Core::DebugPrintf("Generated alternate AVB MAC %d from %d\n", int(result),
                    signedWord(serial));
  return result;
}
void TCard::printStatus() {
  NOAAStatusProperty status(std::array<unsigned char, 52>{});
  getStatusProperty(status);
  Core::DebugPrintf("======== IO Card Status =========\n");
  Core::DebugPrintf(" Card Type:%d (%s)\n", signedWord(word(status, 8)),
                    getCardCString());
  const auto arm = word(status, 0xc);
  Core::DebugPrintf("      ARMv:%d.%d.%d.%d\n", int((arm >> 24) & 31),
                    int((arm >> 20) & 15), int((arm >> 16) & 15),
                    int(arm & 65535));
  const auto fpga = word(status, 0x10);
  Core::DebugPrintf("     FPGAv:%d.%d.%d.%d\n", int((fpga >> 24) & 31),
                    int((fpga >> 20) & 15), int((fpga >> 16) & 15),
                    int(fpga & 65535));
  const auto shelby = word(status, 0x14);
  Core::DebugPrintf("   SHELBYv:%d.%d.%d-%d\n", int(shelby >> 28),
                    int((shelby >> 24) & 15), int((shelby >> 20) & 15),
                    int(shelby & 65535));
  Core::DebugPrintf(" validFPGA:%d\n", int(status.payload[0x26 - 8]));
  Core::DebugPrintf("   mounted:%d\n", int(status.payload[0x28 - 8]));
  Core::DebugPrintf("  ARM comp:%d\n", int(status.payload[0x24 - 8]));
  Core::DebugPrintf(" FPGA comp:%d\n", int(status.payload[0x25 - 8]));
  Core::DebugPrintf(" clock run:%d\n", int(status.payload[0x29 - 8]));
  Core::DebugPrintf("  serial #:%d\n", signedWord(word(status, 0x18)));
  Core::DebugPrintf("    1394 #:%d\n", signedWord(word(status, 0x1c)));
  Core::DebugPrintf("DeviceID #:0x%2X\n", word(status, 0x20));
  Core::DebugPrintf("==============================\n");
}
} // namespace Presonus::NOAA
