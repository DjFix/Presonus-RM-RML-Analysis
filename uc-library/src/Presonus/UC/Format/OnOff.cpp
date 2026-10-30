#include "presonus/uc/OnOff.hpp"
#include <cstring>
#include <strings.h>
namespace Presonus::UC::Format {
OnOff::OnOff(const char *name, const char *on, const char *off)
    : Core::Formatter(name), on_(on), off_(off) {}
OnOff::~OnOff() = default;
void OnOff::print(Core::Formatter::Data &data) const {
  // Original strcpy ignores Data::size. Valid writable capacity and a nonnull
  // selected label are required; no invented truncation or null-print behavior.
  std::strcpy(data.string, data.value == 0.f ? off_ : on_);
}
bool OnOff::scan(Core::Formatter::Data &data) const {
  const char *text = data.string ? data.string : "";
  if (::strcasecmp(text, on_ ? on_ : "") == 0 || std::strcmp(text, "1") == 0) {
    data.value = 1.f;
    return true;
  }
  if (::strcasecmp(text, off_ ? off_ : "") == 0 ||
      std::strcmp(text, "0") == 0) {
    data.value = 0.f;
    return true;
  }
  return false;
}
} // namespace Presonus::UC::Format
