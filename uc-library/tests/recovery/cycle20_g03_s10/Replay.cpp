#include "presonus/surface/MonitorPageComponent.hpp"

#include <cstdlib>
#include <iostream>

using namespace Core::Portable;
using Page = Presonus::Surface::MonitorPageComponent;

namespace {

class Observer final : public ParamObserverBase {
public:
  void paramChanged(Parameter *, int) override { ++notifications; }
  unsigned notifications = 0;
};

bool run(float initial, bool) {
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  info.tag = 1007;
  info.minValue = -1;
  info.maxValue = 1;
  Component registry;
  Page page(Page::SourcePortConstruction{}, registry);
  registry.addParameters(&info, 1);
  auto *parameter = registry.getParameterByTag(info.tag);
  if (!parameter)
    return false;
  parameter->setValue(initial, false);
  Observer observer;
  parameter->addObserver(&observer);
  page.Page::disconnectMappables();
  const bool unchanged = registry.getParameterByTag(info.tag) == parameter &&
                         parameter->getValue() == initial &&
                         observer.notifications == 0 &&
                         !page.monitorSelectionInProgress();
  parameter->removeObserver(&observer);
  return unchanged;
}

} // namespace

int main() {
  for (float initial : {-0.25f, 0.75f}) {
    if (!run(initial, false))
      return 1;
    std::cout << initial << " member unchanged\n";
  }
}
