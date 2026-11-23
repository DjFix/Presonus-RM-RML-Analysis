#include "presonus/PageComponent.hpp"
#include "presonus/MainLCDComponent.hpp"

namespace Presonus {
PageComponent::PageComponent(const char *name, const char *formName, int tag)
    : Component(name), observedTag_(tag), formName_(formName) {}
void PageComponent::onWheelInput(const Core::Portable::WheelEvent &) {}
MainLCDComponent *PageComponent::typedMainScreen() const {
  auto *parent = getParent();
  return parent ? static_cast<MainLCDComponent *>(parent->castTo(1296843588))
                : nullptr;
}
void PageComponent::onShow(bool) {}
int PageComponent::getPageTag() const { return observedTag_; }
const char *PageComponent::getFormName() const { return formName_.str(); }
void *PageComponent::castTo(int classId) {
  return classId == 1348560741 || classId == 1131375984 ? this : nullptr;
}
void *PageComponent::getMainScreen() const {
  if (!bindings_)
    return typedMainScreen();
  return owner_ ? bindings_->castOwner(owner_, 1296843588) : nullptr;
}
bool PageComponent::isVisible() const {
  if (!bindings_) {
    auto *screen = typedMainScreen();
    return screen && screen->getCurrentPage() == this;
  }
  void *screen = getMainScreen();
  return screen && bindings_->currentPage(screen) == this;
}
void PageComponent::stopTextInput(bool cancel) const {
  if (!bindings_) {
    if (auto *screen = typedMainScreen())
      screen->stopTextInput(cancel);
  } else if (void *screen = getMainScreen()) {
    bindings_->stopTextInput(screen, cancel);
  }
}
bool PageComponent::isEditingText() const {
  if (!bindings_) {
    auto *screen = typedMainScreen();
    return screen && screen->isEditingText();
  }
  void *screen = getMainScreen();
  return screen && bindings_->isEditingText(screen);
}
} // namespace Presonus
