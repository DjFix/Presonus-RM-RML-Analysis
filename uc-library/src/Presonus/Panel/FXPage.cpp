#include "presonus/panel/FXPage.hpp"
namespace Presonus::Panel {
void FXPage::prepare() {
  const float value = state.parameter ? state.parameter->getValue() : 1.f;
  // Preserve the native upper comparison and short-circuit ordering. The
  // validated domain contains finite values/bounds, including reversed bounds.
  state.inRange = value > state.upper || value < state.lower ? 0 : 1;
}
} // namespace Presonus::Panel
