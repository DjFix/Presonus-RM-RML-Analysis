#include "presonus/PageComponent.hpp"

namespace Presonus {
void *PageComponent::castTo(int classId) {
  return classId == 1348560741 || classId == 1131375984 ? this : nullptr;
}
void *PageComponent::getMainScreen() const {
  return owner_ ? bindings_.castOwner(owner_, 1296843588) : nullptr;
}
bool PageComponent::isVisible() const {
  void *screen = getMainScreen();
  return screen && bindings_.currentPage(screen) == this;
}
void PageComponent::stopTextInput(bool cancel) const {
  if (void *screen = getMainScreen())
    bindings_.stopTextInput(screen, cancel);
}
bool PageComponent::isEditingText() const {
  void *screen = getMainScreen();
  return screen && bindings_.isEditingText(screen);
}
} // namespace Presonus
