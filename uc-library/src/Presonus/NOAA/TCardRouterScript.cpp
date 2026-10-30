#include "core/portable/corefile.h"
#include "core/system/coredebug.h"
#include "presonus/application/SimpleReader.hpp"
#include "presonus/noaa/router.hpp"
#include <cstdint>
#include <cstdio>
#include <cstring>

namespace {
using Word = Core::CStringBuffer<64>;
bool starts(const Word &word, const char *prefix) {
  return std::strncmp(word.str(), prefix, std::strlen(prefix)) == 0;
}
bool integer(const char *text, long long &value) {
  value = 0;
  return std::sscanf(text, "%lld", &value) == 1;
}
bool stereo(const Word &word, unsigned int left, std::uint32_t &channel) {
  const auto last = word.lastChar();
  if (last == 'l') {
    channel = left;
    return true;
  }
  if (last == 'r') {
    channel = left + 1;
    return true;
  }
  return false;
}
bool sourceChannel(const Word &word, unsigned int device,
                   std::uint32_t &channel) {
  long long value;
  if (starts(word, "mic")) {
    if (!integer(word.str() + 3, value))
      return false;
    channel = static_cast<std::uint32_t>(value) - 1u;
    return true;
  }
  if (starts(word, "tapein"))
    return stereo(word, 38, channel);
  if (starts(word, "auxina"))
    return stereo(word, 32, channel);
  if (starts(word, "auxinb"))
    return stereo(word, 34, channel);
  if (starts(word, "talkback")) {
    channel = 36;
    return true;
  }
  if (!integer(word.str(), value))
    return false;
  if (device == 2 || device == 6) {
    channel = static_cast<std::uint32_t>(value);
    return true;
  }
  if (device != 0)
    return false;
  channel =
      static_cast<std::uint32_t>(value) + (value > 7 ? std::uint32_t(-8) : 56u);
  return true;
}
bool destinationChannel(const Word &word, unsigned int device,
                        std::uint32_t &channel) {
  long long value;
  if (starts(word, "croom"))
    return stereo(word, 40, channel);
  if (starts(word, "main"))
    return stereo(word, 60, channel);
  if (starts(word, "phones"))
    return stereo(word, 38, channel);
  if (starts(word, "sub")) {
    if (!integer(word.str() + 3, value))
      return false;
    channel = static_cast<std::uint32_t>(value) + 55u;
    return true;
  }
  if (starts(word, "aux")) {
    if (!integer(word.str() + 3, value))
      return false;
    channel = static_cast<std::uint32_t>(value) + 41u;
    return true;
  }
  if (device != 0 && device != 2 && device != 6)
    return false;
  if (!integer(word.str(), value))
    return false;
  channel = static_cast<std::uint32_t>(value);
  return true;
}
int signedWord(std::uint32_t word) {
  int value;
  static_assert(sizeof(value) == sizeof(word));
  std::memcpy(&value, &word, sizeof(value));
  return value;
}
} // namespace
namespace Presonus::NOAA {
void TCardRouter::routeScript(const char *filename) {
  // Intentional source port: original app consumed getHomeDir() pointer;
  // pinned actual CCL fills a FileName reference. No legacyCore provider.
  Core::Portable::FileName home;
  Core::Portable::FileUtils::getHomeDir(home);
  Core::CStringBuffer<256> path(home.str());
  if (path.length() < 255)
    path.append("/");
  if (filename && filename[0])
    path.append(filename);
  Core::Portable::FileStream stream;
  if (!stream.open(path.str(), 3)) {
    Core::DebugPrintf("routeScript: file exists but couldn't be opened: %s\n",
                      path.str());
    return;
  }
  Presonus::SimpleReader reader(stream);
  Core::CStringBuffer<256> line;
  std::uint32_t lineNumber = 0;
  while (true) {
    const auto start = stream.getPosition();
    if (!reader.getNextLine(line))
      break;
    const auto next = stream.getPosition();
    Core::CStringBuffer<256> original(line.str());
    line.toLowercase();
    ++lineNumber;
    if (std::strncmp(line.str(), "route", 5) != 0)
      continue;
    stream.setPosition(start, Core::IO::kSeekSet);
    Word word;
    unsigned int source = 0, destination = 0;
    std::uint32_t input = 0, output = 0;
    bool valid =
        reader.getNextWord(word, '\t') && reader.getNextWord(word, '\t');
    if (valid) {
      word.toLowercase();
      if (word == "adc40")
        source = 1;
      else if (word == "1394")
        source = 6;
      else if (word == "muted")
        source = 2;
      else if (word == "dsp")
        source = 0;
      else
        valid = false;
    }
    if (valid) {
      valid = reader.getNextWord(word, '\t');
      if (valid) {
        word.toLowercase();
        valid = sourceChannel(word, source, input);
      }
    }
    if (valid) {
      valid = reader.getNextWord(word, '\t');
      if (valid) {
        word.toLowercase();
        if (word == "dac24")
          destination = 1;
        else if (word == "1394")
          destination = 6;
        else if (word == "spdif")
          destination = 2;
        else if (word == "dsp")
          destination = 0;
        else
          valid = false;
      }
    }
    if (valid) {
      valid = reader.getNextWord(word, '\t');
      if (valid) {
        word.toLowercase();
        valid = destinationChannel(word, destination, output);
      }
    }
    if (!valid) {
      Core::DebugPrintf("error parsing line %d.  %s\n", signedWord(lineNumber),
                        original.str());
      reader.setPosition(next);
      continue;
    }
    if (source == 1)
      input = lookupADCSlot(static_cast<unsigned char>(input));
    if (destination == 1)
      output = lookupDACSlot(static_cast<unsigned char>(output));
    doRouteCommand(static_cast<unsigned char>(destination),
                   static_cast<unsigned char>(output),
                   static_cast<unsigned char>(source),
                   static_cast<unsigned char>(input), 1);
    Core::DebugPrintf(
        "DestID %d; Dest Channel %d; SourceID %d; Source Channel %d\n",
        int(destination), signedWord(output), int(source), signedWord(input));
  }
}
} // namespace Presonus::NOAA
