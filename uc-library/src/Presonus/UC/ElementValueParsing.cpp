#include "presonus/uc/element.hpp"
#include <cstdint>
#include <cstdio>
#include <cstring>
namespace Presonus::UC {
bool Element::parseValue(double &value, const char *source) const {
  if (!source)
    source = "";
  if (std::strchr(source, '#') == source) {
    unsigned long long bits = 0;
    std::sscanf(source + 1, "%llx", &bits);
    std::int64_t signedValue;
    static_assert(sizeof(bits) == sizeof(signedValue));
    std::memcpy(&signedValue, &bits, sizeof(bits));
    value = static_cast<double>(signedValue);
    return true;
  }
  double parsed = 0;
  if (std::sscanf(source, "%lf", &parsed) != 1)
    return false;
  value = parsed;
  return true;
}
} // namespace Presonus::UC
