#include "presonus/surface/ControlName.hpp"
#include <cstdint>
#include <cstring>
namespace Presonus::Surface {
ControlName::ControlName(const char *prefix, int index) {
  static_assert(sizeof(int) == sizeof(std::uint32_t));
  auto bits = static_cast<std::uint32_t>(index) + 1u;
  int number;
  std::memcpy(&number, &bits, sizeof(number));
  value_.appendFormat("%s_%02d", prefix, number);
}
} // namespace Presonus::Surface
