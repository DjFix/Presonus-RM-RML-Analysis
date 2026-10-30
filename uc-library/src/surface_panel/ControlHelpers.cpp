#include "presonus/surface_panel/ControlHelpers.hpp"
#include <cstring>

namespace Presonus::Panel {
std::uint16_t SevenSegControl::convertCharToBmp(char character,
                                                bool decimalPoint) const {
  constexpr std::uint16_t digits[] = {126, 12,  182, 158, 204,
                                      218, 250, 14,  254, 206};
  constexpr std::uint16_t letters[] = {
      238, 248, 114, 188, 242, 226, 122, 232, 96, 28,  236, 112, 170,
      110, 184, 230, 206, 160, 218, 240, 124, 56, 236, 236, 220, 182};
  const auto value = static_cast<unsigned char>(character);
  std::uint16_t bitmap = 0x80;
  if (value >= '0' && value <= '9')
    bitmap = digits[value - '0'];
  else if (value >= 'A' && value <= 'Z')
    bitmap = letters[value - 'A'];
  else if (value >= 'a' && value <= 'z')
    bitmap = letters[value - 'a'];
  else if (value == ' ')
    bitmap = 0;
  else if (value == '_')
    bitmap = 0x10;
  return static_cast<std::uint16_t>(bitmap | (decimalPoint ? 1 : 0));
}
} // namespace Presonus::Panel
namespace Presonus::Surface {
int PanelRegistrar::mapGroupIdToControlType(
    Presonus::Panel::ControlRegistrar::ControlType group) const {
  const auto value = static_cast<int>(group);
  if (value == 1)
    return 13;
  if (value == 2)
    return 16;
  if (value == 0)
    return 100;
  return -1;
}
bool SurfaceRootComponent::isTransportControl(const char *controlName) {
  return std::strncmp(controlName ? controlName : "", "transport_", 10) == 0;
}
} // namespace Presonus::Surface
