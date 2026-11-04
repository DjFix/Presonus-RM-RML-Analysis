#include "presonus/MainLCDComponent.hpp"

namespace Presonus {
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
