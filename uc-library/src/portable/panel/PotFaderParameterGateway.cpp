#include "presonus/panel/pot_fader_control.hpp"
#include <cstdlib>
#include <cstring>
#include <limits>
namespace presonus::panel_binding {
void potFaderParameterCommand(Core::Portable::Parameter &p, unsigned op,
                              std::uint32_t argument) {
  static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559 &&
                std::numeric_limits<float>::digits == 24);
  float value;
  std::memcpy(&value, &argument, sizeof(value));
  switch (op) {
  case 0:
    p.setNormalized(value, true);
    break;
  case 1:
    p.beginEdit();
    break;
  case 2:
    p.endEdit();
    break;
  default:
    std::abort();
  }
}
} // namespace presonus::panel_binding
