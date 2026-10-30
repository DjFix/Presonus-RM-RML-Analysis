#include "presonus/surface/mapping_input_routes.hpp"
#include <cstdint>
namespace Presonus::Surface {
void MappingComponent::verifyRadioGroup(Core::Portable::Parameter *parameter,
                                        int first, int last,
                                        RadioOffBehaviour off) {
  int selected;
  if (parameter->getValue() < 1.f) {
    switch (static_cast<int>(off)) {
    case 0:
      selected = parameter->getTag();
      break;
    case 1:
      selected = -1;
      break;
    case 2:
      selected = first;
      break;
    case 3:
      selected = last;
      break;
    default:
      return;
    }
  } else {
    selected = parameter->getTag();
  }
  setRadioGroup(selected, first, last, false);
}
void MappingComponent::verifyRadioParam(Core::Portable::Parameter *parameter) {
  if (encoderHandler_ && encoderHandler_->handleMappingRadioGroup(parameter))
    return;
  const auto tag = static_cast<std::uint32_t>(parameter->getTag());
  if (tag - 34U <= 3U)
    verifyRadioGroup(parameter, 34, 37, static_cast<RadioOffBehaviour>(1));
  else if (tag - 13U <= 20U)
    verifyRadioGroup(parameter, 13, 33, static_cast<RadioOffBehaviour>(3));
  else if (tag <= 6U)
    verifyRadioGroup(parameter, 0, 6, static_cast<RadioOffBehaviour>(0));
}
} // namespace Presonus::Surface
