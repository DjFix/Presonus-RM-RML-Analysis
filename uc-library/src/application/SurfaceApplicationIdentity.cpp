#include "core/public/corestringbuffer.h"
#include "core/system/coredebug.h"
#include "presonus/application/SurfaceApplication.hpp"
#include <cstdio>

namespace Presonus::Surface {
std::uint64_t SurfaceApplication::getAlternateMac() {
  Core::CStringBuffer<32> decimal;
  Core::CStringBuffer<32> word;
  decimal.appendFormat("%08u", serial_);
  unsigned first = 0, middle = 0, last = 0;
  decimal.subString(word, 0, 2);
  std::sscanf(word.str(), "%u", &first);
  decimal.subString(word, 2, 2);
  std::sscanf(word.str(), "%u", &middle);
  decimal.subString(word, 4, 4);
  std::sscanf(word.str(), "%u", &last);
  first += 30;
  Core::CStringBuffer<32> rearranged;
  rearranged.appendFormat("%02d%02d%04d", static_cast<int>(middle),
                          static_cast<int>(first), static_cast<int>(last));
  unsigned value = 0;
  // This is scanf field width eight, including the original truncation quirk.
  std::sscanf(rearranged.str(), "%08u", &value);
  Core::DebugPrintf("Generated alternate AVB MAC 0x%x from 0x%x\n", value,
                    serial_);
  return UINT64_C(0x0000000a92000000) | value;
}
std::uint64_t SurfaceApplication::getNetworkSerial() {
  return getAlternateMac();
}
} // namespace Presonus::Surface
