#include "presonus/surface/MarkerPageComponent.hpp"

#include <cstdlib>
#include <iostream>

using namespace Core::Portable;
using Page = Presonus::Surface::MarkerPageComponent;

namespace {

class Observer final : public ParamObserverBase {
public:
  void paramChanged(Parameter *, int) override { ++notifications; }
  unsigned notifications = 0;
};

[[gnu::noinline, gnu::noipa]] void dispatchVirtual(Page &page,
                                                   Parameter *parameter) {
  page.onChannelParamChanged(nullptr, parameter);
}

bool run(float initial, bool dispatch) {
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  info.tag = 1007;
  info.minValue = -1;
  info.maxValue = 1;
  Page page;
  Component &registry = page;
  registry.addParameters(&info, 1);
  auto *parameter = registry.getParameterByTag(info.tag);
  if (!parameter)
    return false;
  parameter->setValue(initial, false);
  Observer observer;
  parameter->addObserver(&observer);

  if (dispatch)
    dispatchVirtual(page, parameter);
  else
    page.Page::onChannelParamChanged(nullptr, parameter);
  const bool unchanged = registry.getParameterByTag(info.tag) == parameter &&
                         parameter->getValue() == initial &&
                         observer.notifications == 0 &&
                         page.isLocateMode() == (initial > 0.f);
  parameter->removeObserver(&observer);
  return unchanged;
}

} // namespace

int main() {
  for (float initial : {-0.25f, 0.75f}) {
    if (!run(initial, false))
      return 1;
    std::cout << initial << " member unchanged\n";
    if (!run(initial, true))
      return 1;
    std::cout << initial << " virtual unchanged\n";
  }
}
