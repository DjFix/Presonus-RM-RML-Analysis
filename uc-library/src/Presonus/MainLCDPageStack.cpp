#include "core/portable/gui/coreview.h"
#include "presonus/MainLCDComponent.hpp"

namespace Presonus {

void MainLCDComponent::prenotifyDestroy(
    Core::Portable::ContainerView *container) {
  if (!container)
    return;
  if (auto *owner = container->getOwner()) {
    owner->viewDestroyed(container);
    container->setOwner(nullptr);
  }

  const auto &children = container->getChildren();
  for (int index = 0, count = children.count(); index < count; ++index) {
    if (auto *childContainer = children.at(index)->asContainer())
      prenotifyDestroy(childContainer);
  }
}

// Source-port state uses the pinned CCL container implementation. Original ARM
// storage layout, ownership and ordinary return declarations remain unresolved.
void MainLCDComponent::pushBackPage(PageComponent *page) {
  state.stackConfigured = true;
  if (state.backPages.count() == 9)
    state.backPages.removeFirst();
  state.backPages.add(page);
}

PageComponent *MainLCDComponent::popBackPage() {
  state.stackConfigured = true;
  if (state.backPages.isEmpty())
    return nullptr;
  PageComponent *page = state.backPages.last();
  state.backPages.removeLast();
  return page;
}
} // namespace Presonus
