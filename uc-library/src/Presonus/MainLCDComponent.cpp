#include "presonus/MainLCDComponent.hpp"
#include "core/portable/gui/corecontrols.h"
namespace Presonus {
bool MainLCDComponent::hasBackPage() const {
  return state.stackConfigured ? !state.backPages.isEmpty()
                               : state.back != nullptr;
}
PageComponent *MainLCDComponent::getCurrentPage() const {
  return state.next ? state.next : state.current;
}
bool MainLCDComponent::isEditingText() const {
  return state.lcd &&
         Core::Portable::TextInput::isEditing(application.rootView(state.lcd));
}
void MainLCDComponent::onDestroyed(const LcdView &view) {
  if (state.lcd == &view)
    state.lcd = nullptr;
}
void MainLCDComponent::setLcdView(LcdView *view) {
  state.lcd = view;
  if (view)
    application.observeView(view, *this);
}
void MainLCDComponent::stopTextInput(bool canceled) const {
  if (state.lcd)
    Core::Portable::TextInput::stop(application.rootView(state.lcd), canceled);
}
void MainLCDComponent::onIdle() {
  Core::Portable::Component::onIdle();
  application.showNextPage();
}
void MainLCDComponent::showPage(int tag) {
  if (PageComponent *page = application.findPage(tag))
    application.requestPage(page);
}
void *MainLCDComponent::castTo(int type) {
  return type == 1296843588 || type == 1131375984 ? this : nullptr;
}
void MainLCDComponent::showStartPage() { showPage(application.startPageTag()); }
} // namespace Presonus
