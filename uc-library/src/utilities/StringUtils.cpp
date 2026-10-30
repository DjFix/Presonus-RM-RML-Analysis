#include "presonus/utilities/string_utils.hpp"
#include <cctype>
#include <cstring>
#include <cwctype>

namespace StringUtils {
// Preserve the original L-encoded internal linkage and original scope text.
// Void is the independent source-port declaration; original returns unresolved.
[[gnu::used, gnu::noinline]] static void
removeWhitespace(Core::CStringBuffer<256> &text) {
  Core::CStringBuffer<64> temporary;
  for (const unsigned char *p =
           reinterpret_cast<const unsigned char *>(text.str());
       *p; ++p) {
    if (!std::iswspace(*p)) {
      const char unit[] = {static_cast<char>(*p), 0};
      temporary.append(unit);
    }
  }
  text = temporary.str();
}

[[gnu::used, gnu::noinline]] static void
makeProperMixedCase(Core::CStringBuffer<256> &text) {
  for (int index = 0; index < text.length(); ++index) {
    auto *buffer = text.getBuffer();
    if (index == 0 ||
        std::iswspace(static_cast<unsigned char>(buffer[index - 1]))) {
      const unsigned char value = static_cast<unsigned char>(buffer[index]);
      const int last = text.length() - 1;
      std::memmove(buffer + index, buffer + index + 1,
                   static_cast<std::size_t>(last - index));
      buffer[last] = 0;
      const char unit[] = {static_cast<char>(std::toupper(value)), 0};
      text.insert(index, unit);
    }
  }
}
} // namespace StringUtils

namespace presonus::utilities {
void removeWhitespace(Core::CStringBuffer<256> &text) {
  StringUtils::removeWhitespace(text);
}
void makeProperMixedCase(Core::CStringBuffer<256> &text) {
  StringUtils::makeProperMixedCase(text);
}
} // namespace presonus::utilities
