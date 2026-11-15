#include "presonus/MainLCDComponent.hpp"
#include "core/portable/gui/corecontrols.h"
#include "presonus/PageComponent.hpp"
#include <stdexcept>
namespace Presonus {
MainLCDComponent::MainLCDComponent()
    : Core::Portable::Component(""), state(ownedState) {
  ownedState.stackConfigured = true;
}
presonus::mainlcd_port::Application &
MainLCDComponent::requireApplication() const {
  if (!application)
    throw std::logic_error("MainLCD application is unbound");
  return *application;
}
bool MainLCDComponent::hasBackPage() const {
  return state.stackConfigured ? !state.backPages.isEmpty()
                               : state.back != nullptr;
}
PageComponent *MainLCDComponent::getCurrentPage() const {
  return state.next ? state.next : state.current;
}
int MainLCDComponent::getCurrentPageTag() const {
  const PageComponent *page = getCurrentPage();
  return page ? page->getPageTag() : -1;
}
void MainLCDComponent::setupBackPage() {
  if (!state.current || !state.next)
    return;
  if (state.next->observedByte89() == 0) {
    state.back = nullptr;
    return;
  }
  if (state.current->getPageTag() != -1000)
    pushBackPage(state.current);
}
bool MainLCDComponent::isEditingText() const {
  return state.lcd && Core::Portable::TextInput::isEditing(
                          requireApplication().rootView(state.lcd));
}
void MainLCDComponent::onDestroyed(const LcdView &view) {
  if (state.lcd == &view)
    state.lcd = nullptr;
}
void MainLCDComponent::setLcdView(LcdView *view) {
  state.lcd = view;
  if (view)
    requireApplication().observeView(view, *this);
}
void MainLCDComponent::stopTextInput(bool canceled) const {
  if (state.lcd)
    Core::Portable::TextInput::stop(requireApplication().rootView(state.lcd),
                                    canceled);
}
void MainLCDComponent::onIdle() {
  Core::Portable::Component::onIdle();
  requireApplication().showNextPage();
}
void MainLCDComponent::showPage(int tag) {
  if (PageComponent *page = requireApplication().findPage(tag))
    requireApplication().requestPage(page);
}
void *MainLCDComponent::castTo(int type) {
  return type == 1296843588 || type == 1131375984 ? this : nullptr;
}
void MainLCDComponent::showStartPage() {
  showPage(requireApplication().startPageTag());
}
} // namespace Presonus
