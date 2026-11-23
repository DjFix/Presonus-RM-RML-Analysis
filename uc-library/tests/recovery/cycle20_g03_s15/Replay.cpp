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

// The real interface is used. Any attempted service invocation is a failure.
class TrapController final : public Presonus::IMappingController {
public:
  int getModifiers() const override { std::abort(); }
  int getRadioValue(int, int) const override { std::abort(); }
  int getBankScrollingOffset() const override { std::abort(); }
  Parameter *getParamByTag(int) const override { std::abort(); }
  Parameter *getMainScreenParamByTag(int) const override { std::abort(); }
  bool isDisplayEncoderLocked() const override { std::abort(); }
  bool areFadersLockedToMainMix() const override { std::abort(); }
  void encoderChanged(int) const override { std::abort(); }
  void onSelectedChannelChanged() override { std::abort(); }
  void selectedChannelUpdated() override { std::abort(); }
  void setRadioGroup(int, int, int, bool) override { std::abort(); }
  void onDeviceDisconnected() override { std::abort(); }
};

[[gnu::noinline, gnu::noipa]] void
dispatchVirtual(Page &page, Presonus::IMappingController *controller) {
  page.setMappingController(controller);
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

  TrapController liveController;
  auto *controller = initial > 0 ? &liveController : nullptr;
  if (dispatch)
    dispatchVirtual(page, controller);
  else
    page.Page::setMappingController(controller);
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
