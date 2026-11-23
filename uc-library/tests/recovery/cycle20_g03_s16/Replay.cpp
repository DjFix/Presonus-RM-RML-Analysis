#include "presonus/surface/CapturePageComponent.hpp"

#include "presonus/surface/sl_mixer_encoder.hpp"

#include <cstdlib>
#include <iostream>

using namespace Core::Portable;
using Page = Presonus::Surface::CapturePageComponent;

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

// Borrowed app adapters are real typed interfaces. No target call is
// expected to reach them, so every adapter entry is a failure.
class TrapPageBindings final : public presonus::page::Bindings {
public:
  void *castOwner(void *, int) const override { std::abort(); }
  const void *currentPage(void *) const override { std::abort(); }
  void stopTextInput(void *, bool) const override { std::abort(); }
  bool isEditingText(void *) const override { std::abort(); }
};

class TrapCaptureBindings final : public presonus::capture::Bindings {
public:
  using Client = Presonus::DAWClientComponent;
  Core::Vector<void *> &observers(Client *) const override { std::abort(); }
  Component *document(Client *) const override { std::abort(); }
  Component *recordDiskSpace(Client *) const override { std::abort(); }
  Component *session(Client *) const override { std::abort(); }
  Component *arrangement(Client *) const override { std::abort(); }
  void *timeInfo(Client *) const override { std::abort(); }
  void *castTimeInfo(void *) const override { std::abort(); }
  bool progress(Client *) const override { std::abort(); }
  void setDelegate(Client *) const override { std::abort(); }
  void baseOnShow(bool) const override { std::abort(); }
  void showStartPage(void *) const override { std::abort(); }
  void *modalPage(void *) const override { std::abort(); }
  void *castLoadPage(void *) const override { std::abort(); }
  void closeLoadPage(void *) const override { std::abort(); }
  void setTimeMode(void *, int) const override { std::abort(); }
  void setTimeFormat(void *, int) const override { std::abort(); }
  void wheel(void *, int) const override { std::abort(); }
  void *createDocumentPage(Client *, const char *,
                           const char *) const override {
    std::abort();
  }
  void showModal(void *, void *) const override { std::abort(); }
  void command(Client *, const char *, const char *) const override {
    std::abort();
  }
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
  Component registry;
  TrapPageBindings pageBindings;
  TrapCaptureBindings captureBindings;
  Presonus::PageComponent containingPage(nullptr, pageBindings, "Capture");
  containingPage.bindObservedPageState(91, 17);
  registry.addParameters(&info, 1);
  auto *parameter = registry.getParameterByTag(info.tag);
  if (!parameter)
    return false;
  parameter->setValue(initial, false);
  Page page(registry, containingPage, captureBindings, nullptr, parameter);
  Observer observer;
  parameter->addObserver(&observer);

  TrapController liveController;
  auto *controller = initial > 0 ? &liveController : nullptr;
  if (dispatch)
    dispatchVirtual(page, controller);
  else
    page.Page::setMappingController(controller);
  const bool unchanged =
      registry.getParameterByTag(info.tag) == parameter &&
      parameter->getValue() == initial && observer.notifications == 0 &&
      page.portableDAW() == nullptr && page.portableSoundcheck() == parameter &&
      containingPage.observedByte89() == 17 &&
      containingPage.getPageTag() == 91;
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
