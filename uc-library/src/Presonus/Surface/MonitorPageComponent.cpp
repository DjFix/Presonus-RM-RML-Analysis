#include "presonus/surface/MonitorPageComponent.hpp"
namespace Presonus::Surface {
void MonitorPageComponent::applyMonitorSelection() {
  selectionBusy_ = true;
  for (int tag = 101;; ++tag) {
    auto *parameter = parameters_.getParameterByTag(tag);
    if (!parameter || !(parameter->getValue() > 0.f))
      continue;
    if (auto *destination = parameters_.findParameter("monitorlist"))
      destination->fromString(parameter->getTitle(false), true);
    selectionBusy_ = false;
    return;
  }
}

void MonitorPageComponent::radioSelection(Core::Portable::Parameter *selected,
                                          int first, int last) {
  const int selectedTag = selected->getTag();
  if (first > selectedTag || last < selectedTag || first > last)
    return;
  for (int tag = first; tag <= last; ++tag) {
    auto *parameter = parameters_.getParameterByTag(tag);
    if (parameter)
      parameter->setValue(parameter->getTag() == selected->getTag() ? 1.f : 0.f,
                          false);
  }
}
} // namespace Presonus::Surface
