#include "presonus/MainLCDComponent.hpp"
#include "core/portable/gui/corecontrols.h"
#include "presonus/PageComponent.hpp"
#include <stdexcept>
namespace Presonus {
MainLCDComponent::MainLCDComponent()
    : Core::Portable::Component(""), state(ownedState) {
  ownedState.stackConfigured = true;
}
MainLCDComponent::~MainLCDComponent() {
  if (state.lcd && state.viewObserverSlot)
    *state.viewObserverSlot = nullptr;
  state.current = nullptr;
  // CCL vectors own their buffers, not the borrowed pointer elements.
  state.pages.removeAll();
  state.views.removeAll();
}
presonus::mainlcd_port::Application &
MainLCDComponent::requireApplication() const {
  if (!application)
    throw std::logic_error("MainLCD application is unbound");
  return *application;
}
PageComponent *MainLCDComponent::getPageByTag(int tag) const {
  const int count = countChildren();
  for (int i = 0; i < count; ++i) {
    auto *child = getChild(i);
    if (!child)
      continue;
    auto *page = static_cast<PageComponent *>(child->castTo(1348560741));
    if (page && page->getPageTag() == tag)
      return page;
  }
  return nullptr;
}
void MainLCDComponent::syncPageParams() {
  const auto *selected = getCurrentPage();
  const int count = countChildren();
  for (int i = 0; i < count; ++i) {
    auto *child = getChild(i);
    if (!child)
      continue;
    auto *page = static_cast<PageComponent *>(child->castTo(1348560741));
    if (!page)
      continue;
    if (auto *parameter = getParameterByTag(page->getPageTag()))
      parameter->setValue(page == selected ? 1.f : 0.f, false);
  }
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
void MainLCDComponent::showStartPage() { showPage(getStartPageTag()); }
int MainLCDComponent::getStartPageTag() const {
  return requireApplication().startPageTag();
}

void MainLCDComponent::pageAboutToShow(const PageComponent &,
                                       const PageComponent *) {}

void MainLCDComponent::onSelectedChannelChanged() {}

void MainLCDComponent::selectedChannelUpdated() {}

void MainLCDComponent::onFocusControlChanged(Core::Portable::Control *) {}
} // namespace Presonus
