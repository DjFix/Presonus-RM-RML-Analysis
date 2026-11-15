#include "presonus/panel/FXMainPage.hpp"
#include <cstring>
namespace Presonus::Panel {
void FXMainPage::prepare() {
  if (!state_.parameter)
    return;
  if (state_.mode != 3 && state_.mode != 1)
    return;
  const float value = state_.parameter->getValue();
  const bool hasHD = std::strstr(state_.name.c_str(), "HD") != nullptr;
  state_.flag = (value > 1.0f) == hasHD;
}
} // namespace Presonus::Panel
