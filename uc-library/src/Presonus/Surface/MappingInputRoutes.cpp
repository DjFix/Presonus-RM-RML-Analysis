#include "presonus/surface/mapping_input_routes.hpp"
#include <cmath>
#include <cstdint>
#include <stdexcept>
namespace Presonus::Surface {
void MappingComponent::encoderChanged(int index) const {
  if (encoderHandler_)
    encoderHandler_->onEncoderChanged(index);
}
void MappingComponent::handleFootswitch(bool pressed) {
  // Original requires parameter38 and directly dereferences it. Source-port
  // invalid-configuration guards are outside the normal original proof.
  if (countParameters() <= 0)
    throw std::logic_error("mapping footswitch parameter38 required");
  auto *parameter = getParameterByTag(38);
  if (!parameter)
    throw std::logic_error("mapping footswitch parameter38 required");
  const float value = parameter->getValue();
  if (!std::isfinite(value) || value < -2147483648.0f || value >= 2147483648.0f)
    throw std::domain_error("finite int32 footswitch mode required");
  const int mode = static_cast<int>(value);
  auto *handler = static_cast<std::uint32_t>(mode) - 4U <= 1U
                      ? alternateFootswitchHandler_
                      : normalFootswitchHandler_;
  if (handler)
    handler->handleFootswitch(
        static_cast<MixerAssignmentHandler::FootswitchMode>(mode), pressed);
}
} // namespace Presonus::Surface
