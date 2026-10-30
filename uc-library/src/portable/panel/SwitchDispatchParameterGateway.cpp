#include "presonus/panel/switch_control.hpp"
#include <cstdlib>
#include <cstring>
namespace presonus::panel_binding {
std::uint32_t switchParameterDispatch(Core::Portable::Parameter &p, unsigned op,
                                      std::uint32_t arg) {
  float value;
  std::memcpy(&value, &arg, sizeof(value));
  float result = 0;
  switch (op) {
  case 0:
    return p.isEnabled();
  case 1:
    result = p.getMax();
    break;
  case 2:
    result = p.getValue();
    break;
  case 3:
    p.setValue(value, true);
    return 0;
  case 4:
    p.increment(1);
    return 0;
  case 5:
    p.beginEdit();
    return 0;
  case 6:
    p.endEdit();
    return 0;
  default:
    std::abort();
  }
  std::uint32_t bits;
  std::memcpy(&bits, &result, sizeof(bits));
  return bits;
}
} // namespace presonus::panel_binding
