#include "presonus/avb/protocol.hpp"
#include <cstdio>
#include <cstring>

namespace Presonus::AVB {
void AvbManagerBase::macAddressToString(Core::CString256 &text,
                                        unsigned long long value) {
  for (int i = 5; i >= 0; --i)
    text.appendFormat(i ? "%02X:" : "%02X",
                      static_cast<unsigned>((value >> (8 * i)) & 255));
}
unsigned long long
AvbManagerBase::macAddressStringToLong(Core::CString256 &text) {
  char part[3]{};
  unsigned long long result = 0;
  for (int i = 0; i < 6; ++i) {
    if (text.length() > 3 * i) {
      std::strncpy(part, text.str() + 3 * i, 2);
      part[2] = 0;
    }
    unsigned long long octet = 0;
    std::sscanf(part, "%llx", &octet);
    result |= (octet & 255) << (8 * (5 - i));
  }
  return result;
}
} // namespace Presonus::AVB
