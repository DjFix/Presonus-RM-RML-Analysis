#include "presonus/surface/GeqPresetsPageComponent.hpp"
#include <cmath>
#include <limits>
#include <stdexcept>
namespace Presonus::Surface {
GeqPresetsPageComponent::~GeqPresetsPageComponent() = default;
void GeqPresetsPageComponent::paramChanged(Core::Portable::Parameter *parameter,
                                           int message) {
  PresetsPageComponent::paramChanged(parameter, message);
}
void GeqPresetsPageComponent::onShow(bool show) {
  if (show) {
    const Core::CString64 title("GEQ");
    if (auto *parameter = getParameterByTag(1007))
      parameter->fromString(title, false);
  }
  PresetsPageComponent::onShow(show);
}
void GeqPresetsPageComponent::getTargetUrl(Core::CString256 &url) {
  const auto *parameter = findParameter("selected_mix");
  if (!parameter)
    return;

  // The original casts the float via the ARM runtime. Restrict the portable
  // conversion to finite values representable by int.
  const double value = parameter->getValue();
  if (!std::isfinite(value) || value < std::numeric_limits<int>::min() ||
      value > std::numeric_limits<int>::max())
    throw std::out_of_range("selected GEQ is outside the portable index range");
  if (!targets_)
    throw std::logic_error("missing GEQ preset mixer binding");

  const int index = static_cast<int>(value);
  const auto *target =
      index > 19
          ? (index == 20 ? targets_->mainGeq : targets_->alternateMainGeq)
          : (index >= 0 && index < targets_->mixGeqs.count()
                 ? targets_->mixGeqs.at(index)
                 : nullptr);
  if (target)
    target->getComponentPath(url);
}
} // namespace Presonus::Surface
