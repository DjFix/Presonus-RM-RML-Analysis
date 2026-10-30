#include "presonus/application/SimpleReader.hpp"
#include "core/portable/corefile.h"
#include "core/system/coredebug.h"
#include <cstring>

namespace {
Core::int64 nextPosition(Core::int64 position) {
  Core::uint64 bits;
  std::memcpy(&bits, &position, sizeof(bits));
  ++bits;
  std::memcpy(&position, &bits, sizeof(position));
  return position;
}
} // namespace
namespace Presonus {
SimpleReader::SimpleReader(Core::IO::Stream &stream) : stream_(stream) {
  stream_.setPosition(0, Core::IO::kSeekSet);
}
Core::int64 SimpleReader::setPosition(long long position) {
  return stream_.setPosition(position, Core::IO::kSeekSet);
}
bool SimpleReader::advanceToNextChar(char target) const {
  for (unsigned count = 0; count < 4096; ++count) {
    unsigned char byte = 0;
    if (stream_.readBytes(&byte, 1) != 1)
      return false;
    if (byte == static_cast<unsigned char>(target))
      return true;
  }
  return false;
}
bool SimpleReader::advanceToNextWord(const char *word) const {
  if (!word)
    return true;
  const char *current = word;
  bool first = true;
  while (*current) {
    const auto before = stream_.getPosition();
    if (!advanceToNextChar(*current))
      return false;
    const auto after = stream_.getPosition();
    if (!first && after != nextPosition(before)) {
      stream_.setPosition(nextPosition(before), Core::IO::kSeekSet);
      current = word;
    } else {
      ++current;
    }
    first = false;
  }
  return true;
}
bool SimpleReader::getNextWord(Core::CStringBuffer<64> &out,
                               char delimiter) const {
  out.getBuffer()[0] = 0;
  for (unsigned count = 0; count < 64; ++count) {
    unsigned char byte = 0;
    if (stream_.readBytes(&byte, 1) != 1)
      return false;
    if (byte == static_cast<unsigned char>(delimiter)) {
      if (out.length() != 0)
        return true;
    } else if (byte == '\n') {
      return true;
    } else if (byte != '\r') {
      const char text[] = {static_cast<char>(byte), 0};
      out.append(text);
    }
  }
  return false;
}
bool SimpleReader::getNextLine(Core::CStringBuffer<256> &out) const {
  out.getBuffer()[0] = 0;
  for (unsigned count = 0; count < 256; ++count) {
    unsigned char byte = 0;
    if (stream_.readBytes(&byte, 1) != 1)
      return out.length() != 0;
    if (byte == '\n')
      return true;
    if (byte != '\r') {
      const char text[] = {static_cast<char>(byte), 0};
      out.append(text);
    }
  }
  return false;
}
bool SimpleReader::getValueForKey(Core::CStringBuffer<64> &out,
                                  const Core::ConstString &key) const {
  Core::CStringBuffer<64> word;
  if (!getNextWord(word, '='))
    return false;
  if (!(word == key.str()))
    return true;
  getNextWord(word, '\t');
  if (word.length() != 0) {
    // Original copies all 64 bytes, including unspecified stack tail. Only
    // initialized string prefix is claimed; no deterministic tail is invented.
    out = word;
  } else {
    Core::DebugPrintf("getValueForKey: didn't find a name after the %s tag\n",
                      key.str());
  }
  return true;
}
bool SimpleReader::findValueForKey(Core::CStringBuffer<64> &out,
                                   const Core::ConstString &key) const {
  stream_.setPosition(0, Core::IO::kSeekSet);
  while (getValueForKey(out, key)) {
    if (out.length() != 0)
      break;
  }
  return out.length() != 0;
}
void SimpleReader::getValueForKey(Core::CStringBuffer<64> &out,
                                  const Core::ConstString &key,
                                  const Core::ConstString &path) {
  if (!Core::Portable::FileUtils::fileExists(path.str()))
    return;
  Core::Portable::FileStream stream;
  if (stream.open(path.str(), Core::IO::kReadMode | Core::IO::kWriteMode)) {
    SimpleReader reader(stream);
    reader.getValueForKey(out, key);
  } else {
    Core::DebugPrintf("SimpleReader::getValueForKey: file exists but couldn't "
                      "be opened: %s\n",
                      path.str());
  }
}
} // namespace Presonus
