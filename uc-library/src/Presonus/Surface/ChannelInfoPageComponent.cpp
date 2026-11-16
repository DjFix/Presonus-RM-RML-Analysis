#include "presonus/surface/ChannelInfoPageComponent.hpp"
namespace Presonus::Surface {
ChannelInfoPageComponent::~ChannelInfoPageComponent() = default;
void ChannelInfoPageComponent::handleLocalSourceSelect(float value) {
  auto *input = findParameter("dig_in");
  auto *option = findParameter("dig_opt");
  if (!input || !option)
    return;
  input->setValue(value, true);
  if (value > 0.f)
    option->setValue(value - 1.f, true);
}
void ChannelInfoPageComponent::handleExternalSourceSelect() {
  auto *input = findParameter("dig_in");
  auto *option = findParameter("dig_opt");
  if (!input || !option)
    return;
  float value = 0.f;
  if (input->getValue() > 0.f)
    value = option->getValue() + 1.f;
  getParameterByTag(1009)->setValue(value, false);
}
} // namespace Presonus::Surface
