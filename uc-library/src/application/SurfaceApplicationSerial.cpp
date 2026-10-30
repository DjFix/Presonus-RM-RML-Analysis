#include "core/portable/corefile.h"
#include "core/public/corestringbuffer.h"
#include "presonus/application/SimpleReader.hpp"
#include "presonus/application/SurfaceApplication.hpp"
#include <algorithm>
#include <cstdio>
#include <cstring>

namespace Presonus::Surface {
void SurfaceApplication::readSerialFromDisk() {
  Core::Portable::FileStream file;
  if (!file.open("/sfs/hwaddr.txt", Core::IO::kReadMode | Core::IO::kWriteMode))
    return;
  Presonus::SimpleReader reader(file);
  Core::CStringBuffer<64> word;
  Core::CStringBuffer<128> combined;
  for (int index = 0; index < 3; ++index) {
    reader.getNextWord(word, ':');
    unsigned long long discarded = 0;
    std::sscanf(word.str(), "%llx", &discarded);
  }
  const auto append = [&] {
    const auto length = std::strlen(word.str());
    const auto available = 127 - std::strlen(combined.str());
    if (length != 0 && available != 0) {
      std::strncat(combined.getBuffer(), word.str(),
                   std::min(length, available));
      combined.getBuffer()[127] = 0;
    }
  };
  while (reader.getNextWord(word, ':'))
    append();
  append(); // The final partial word is retained even when getNextWord is
            // false.
  unsigned long long value = 0;
  std::sscanf(combined.str(), "%llx", &value);
  serial_ = static_cast<std::uint32_t>(value);
}
} // namespace Presonus::Surface
