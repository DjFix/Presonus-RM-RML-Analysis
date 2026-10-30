#pragma once
#include "core/public/corestream.h"
#include "core/public/corestringbuffer.h"

namespace Presonus {
// Source-port candidate. Ordinary return spellings remain unencoded in the
// original ELF; bool/int64/void below require declaration review before ready.
class SimpleReader {
public:
  explicit SimpleReader(Core::IO::Stream &);
  bool advanceToNextChar(char) const;
  bool advanceToNextWord(const char *) const;
  bool getNextWord(Core::CStringBuffer<64> &, char) const;
  bool getNextLine(Core::CStringBuffer<256> &) const;
  bool getValueForKey(Core::CStringBuffer<64> &,
                      const Core::ConstString &) const;
  bool findValueForKey(Core::CStringBuffer<64> &,
                       const Core::ConstString &) const;
  static void getValueForKey(Core::CStringBuffer<64> &,
                             const Core::ConstString &,
                             const Core::ConstString &);
  Core::int64 setPosition(long long);

private:
  Core::IO::Stream &stream_;
};
} // namespace Presonus
