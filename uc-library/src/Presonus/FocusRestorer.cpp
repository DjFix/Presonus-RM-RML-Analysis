#include "presonus/FocusRestorer.hpp"
#include <cstring>
namespace Presonus {
FocusRestorer::FocusInfo::FocusInfo() : observedState{}, name(nullptr) {}
void FocusRestorer::FocusInfo::setView(Core::Portable::View &view) {
  Core::Rect rect;
  view.getClientRect(rect);
  Core::Point point(view.getSize().left, view.getSize().top);
  view.clientToRoot(point);
  observedState = {1449747831U,
                   static_cast<std::uint32_t>(rect.left),
                   static_cast<std::uint32_t>(rect.top),
                   static_cast<std::uint32_t>(rect.right),
                   static_cast<std::uint32_t>(rect.bottom),
                   static_cast<std::uint32_t>(point.x),
                   static_cast<std::uint32_t>(point.y)};
  // Original app copies exactly 32 bytes; preserve that bound independently
  // of upstream's larger current View name buffer. Matching requires a NUL.
  std::memcpy(name.getBuffer(), view.getName().str(), 32);
}
bool FocusRestorer::FindFilter::matches(
    const Core::Portable::View *view) const {
  if (!view || !view->wantsFocus() || info.observedState[0] != 1449747831U)
    return false;
  Core::Rect rect;
  view->getClientRect(rect);
  if (info.observedState[1] != static_cast<std::uint32_t>(rect.left) ||
      info.observedState[2] != static_cast<std::uint32_t>(rect.top) ||
      info.observedState[3] != static_cast<std::uint32_t>(rect.right) ||
      info.observedState[4] != static_cast<std::uint32_t>(rect.bottom))
    return false;
  Core::Point point(view->getSize().left, view->getSize().top);
  view->clientToRoot(point);
  return info.observedState[5] == static_cast<std::uint32_t>(point.x) &&
         info.observedState[6] == static_cast<std::uint32_t>(point.y) &&
         std::strcmp(view->getName().str(), info.name.str()) == 0;
}
} // namespace Presonus

namespace Presonus {
FocusRestorer::FocusRestorer(Core::Portable::ContainerView &container)
    : container_(container), snapshot_() {
  if (auto *root = container_.getRootView())
    if (auto *focus = root->getFocusView())
      snapshot_.setView(*focus);
}
FocusRestorer::~FocusRestorer() {
  if (!snapshot_.observedState[0])
    return;
  auto *root = container_.getRootView();
  if (!root)
    return;
  // Preserve native 32-bit coordinate values without inferring original ARM
  // layout.
  std::int32_t x, y;
  std::memcpy(&x, &snapshot_.observedState[5], sizeof(x));
  std::memcpy(&y, &snapshot_.observedState[6], sizeof(y));
  FindFilter filter(snapshot_);
  if (auto *view = root->findView(Core::Point(x, y), true, &filter))
    root->setFocusView(view);
}
} // namespace Presonus
