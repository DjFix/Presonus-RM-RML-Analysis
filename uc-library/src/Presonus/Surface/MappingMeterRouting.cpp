#include "presonus/surface/mapping_input_routes.hpp"
#include <stdexcept>
namespace Presonus::Surface {
void MappingComponent::setGeqMode(bool enabled) {
  if (enabled) {
    for (int tag = 34; tag <= 37; ++tag) {
      auto *parameter =
          countParameters() > 0 ? getParameterByTag(tag) : nullptr;
      if (!parameter)
        throw std::logic_error("mapping meter parameter missing");
      parameter->setValue(0.f, false);
    }
  }
  if (encoderHandler_)
    encoderHandler_->updateConnections();
}
void MappingComponent::setPreampsMeterMode(bool enabled) {
  if (enabled) {
    for (int tag = 34; tag <= 37; ++tag) {
      auto *parameter =
          countParameters() > 0 ? getParameterByTag(tag) : nullptr;
      if (!parameter)
        throw std::logic_error("mapping meter parameter missing");
      parameter->setValue(0.f, false);
    }
  }
  if (encoderHandler_)
    encoderHandler_->updateConnections();
}
} // namespace Presonus::Surface
