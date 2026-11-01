#include "presonus/surface/CapturePageComponent.hpp"
namespace Presonus::Surface {
using Core::Portable::AliasParam;
using Core::Portable::Component;
using Core::Portable::Parameter;
void CapturePageComponent::onObjectChanged(
    IDAWComponentObserver::ObjectChangeMessage message) {
  if (static_cast<unsigned int>(message) == 2)
    syncInProgressParam();
}
void CapturePageComponent::bindAlias(int localTag, Component *remote,
                                     int remoteTag, bool feedback) {
  if (auto *alias = AliasParam::cast(parameters_.getParameterByTag(localTag))) {
    alias->setOriginal(remote ? remote->getParameterByTag(remoteTag) : nullptr);
    if (feedback)
      alias->setFeedbackNeeded(true);
  }
}
void CapturePageComponent::setDAWComponent(DAWClientComponent *daw) {
  if (daw_)
    bindings_.observers(daw_).remove(this);
  daw_ = daw;
  if (daw_ && !bindings_.observers(daw_).contains(this))
    bindings_.observers(daw_).add(this);
  bindings_.setDelegate(daw_);
  auto *document = daw_ ? bindings_.document(daw_) : nullptr;
  bindAlias(7, document, 1);
  bindAlias(6, document, 0, true);
  auto *server = daw_ ? bindings_.recordDiskSpace(daw_) : nullptr;
  bindAlias(11, server, 0);
  auto *session = daw_ ? bindings_.session(daw_) : nullptr;
  bindAlias(9, session, 5);
  bindAlias(10, session, 10);
  bindAlias(13, session, 9);
  if (soundcheck_)
    soundcheck_->removeObserver(this);
  soundcheck_ = session ? session->getParameterByTag(7) : nullptr;
  if (soundcheck_)
    soundcheck_->addObserver(this);
  syncSoundcheckParam();
  auto *arrangement = daw_ ? bindings_.arrangement(daw_) : nullptr;
  bindAlias(8, arrangement, 10);
  bindAlias(12, arrangement, 2);
  syncInProgressParam();
  if (!daw_ && page_.isVisible())
    if (auto *screen = page_.getMainScreen())
      bindings_.showStartPage(screen);
}
void CapturePageComponent::syncSoundcheckParam() {
  parameters_.getParameterByTag(4)->setValue(
      soundcheck_ ? soundcheck_->getValue() : 0.f, false);
}
void CapturePageComponent::onShow(bool show) {
  if (show) {
    if (daw_) {
      if (auto *time = bindings_.timeInfo(daw_))
        if (auto *concrete = bindings_.castTimeInfo(time)) {
          bindings_.setTimeMode(concrete, 0);
          bindings_.setTimeFormat(concrete, 0);
        }
    } else if (auto *screen = page_.getMainScreen())
      bindings_.showStartPage(screen);
  }
  bindings_.baseOnShow(show);
}
void CapturePageComponent::openSession() {
  if (daw_)
    if (auto *screen = page_.getMainScreen()) {
      auto *modal = bindings_.createDocumentPage(daw_, "documents/recent",
                                                 "Load Session");
      bindings_.showModal(screen, modal);
    }
}
void CapturePageComponent::syncInProgressParam() {
  parameters_.getParameterByTag(5)->setValue(
      daw_ && bindings_.progress(daw_) ? 1.f : 0.f, false);
}
void CapturePageComponent::setSoundcheckMode(Parameter *parameter) {
  auto *document = daw_ ? bindings_.document(daw_) : nullptr;
  auto *session = daw_ ? bindings_.session(daw_) : nullptr;
  if (!document || !session) {
    parameter->setValue(0.f, false);
    return;
  }
  if (parameter->getValue() > 0.f) {
    if (auto *p = document->getParameterByTag(0)) {
      if (p->getValue() > 0.f)
        loadSoundcheckSession();
      syncSoundcheckParam();
    }
  } else if (auto *p = session->getParameterByTag(6))
    if (p->getValue() > 0.f)
      p->setValue(0.f, true);
}
bool CapturePageComponent::loadSoundcheckSession() {
  if (daw_)
    if (auto *screen = page_.getMainScreen()) {
      auto *modal = bindings_.createDocumentPage(daw_, "documents/soundcheck",
                                                 "Soundcheck Session");
      bindings_.showModal(screen, modal);
    }
  return true;
}
void CapturePageComponent::onWheelInput(
    const Core::Portable::WheelEvent &event) {
  if (daw_)
    if (auto *time = bindings_.timeInfo(daw_))
      if (auto *concrete = bindings_.castTimeInfo(time))
        bindings_.wheel(concrete, event.delta);
}
void CapturePageComponent::paramChanged(Parameter *parameter, int message) {
  if (parameter == soundcheck_) {
    syncSoundcheckParam();
    return;
  }
  const int tag = parameter->getTag();
  if (tag == 6) {
    if (parameter->getValue() > 0.f && daw_)
      if (auto *screen = page_.getMainScreen())
        if (auto *modal = bindings_.modalPage(screen))
          if (auto *load = bindings_.castLoadPage(modal))
            bindings_.closeLoadPage(load);
    return;
  }
  if (message != 2)
    return;
  if (tag == 4) {
    setSoundcheckMode(parameter);
    return;
  }
  if (tag < 0 || tag > 3 || !(parameter->getValue() > 0.f) || !daw_)
    return;
  if (tag == 1) {
    openSession();
    return;
  }
  if (tag == 0)
    bindings_.command(daw_, "Session", "New");
  if (tag == 2)
    bindings_.command(daw_, "File", "Close");
  if (tag == 3)
    bindings_.command(daw_, "Session", "Record Now");
}
} // namespace Presonus::Surface
