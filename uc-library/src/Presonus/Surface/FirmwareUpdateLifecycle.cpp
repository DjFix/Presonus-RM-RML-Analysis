#include "presonus/surface_update/FirmwareUpdateComponent.hpp"

namespace Presonus::Surface {
FirmwareUpdateComponent::~FirmwareUpdateComponent() {
  if (worker)
    worker->terminate();
  worker.reset();
}
void FirmwareUpdateComponent::doUpdate() {
  if (!taskParameter)
    taskParameter = getParameterByTag(4);
  class UpgradeTask : public Core::Portable::BackgroundTask {
  public:
    int product;
    int serial;
    Presonus::UUX::FirmwareUpdateListener *listener;
    Core::Portable::Parameter *trigger;
    UpgradeTask(int product, int serial,
                Presonus::UUX::FirmwareUpdateListener *listener,
                Core::Portable::Parameter *trigger)
        : product(product), serial(serial), listener(listener),
          trigger(trigger) {}
    ~UpgradeTask() override {}
    void work() override {
      Presonus::UUX::FirmwareUpdater updater(product, serial, listener);
      Core::CString256 endpoint("surface/cs_upgrade");
      // The native task writes its endpoint directly, clearing animation.
      presonus::uux::PathView::configureTask(updater, endpoint.str());
      presonus::uux::PathView::firmwareVersion(updater, "13840");
      updater.updateFirmware();
      if (trigger)
        trigger->enable(true);
    }
  };
  auto *trigger = getParameterByTag(0);
  worker->addTask(new UpgradeTask(product, serial, this, trigger));
}
void FirmwareUpdateComponent::paramChanged(Core::Portable::Parameter *p,
                                           int msg) {
  (void)p->getValue();
  if (msg == 2) {
    const int tag = p->getTag();
    if (tag == 0) {
      if (p->getValue() == 1.f) {
        doUpdate();
        getParameterByTag(7)->setValue(2.f, false);
      } else if (auto *state = getParameterByTag(7)) {
        if (state->getValue() > 0.f)
          state->setValue(-2.f, false);
      }
    } else if (tag == 5 || tag == 6) {
      if (p->getValue() > 0.f) {
        getParameterByTag(7)->setValue(tag == 5 ? 1.f : 0.f, false);
        if (tag == 6) {
          for (int id : {1, 2, 3})
            getParameterByTag(id)->enable(false);
        }
      }
      p->enable(false);
    }
  }
  Core::Portable::Component::paramChanged(p, msg);
}
} // namespace Presonus::Surface
