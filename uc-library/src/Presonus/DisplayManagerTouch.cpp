#include "presonus/surface/DisplayManager.hpp"
namespace Presonus {
void DisplayManager::screenTouched(const Panel::ControlRegistrar &,
                                   TouchInputEvent e) {
  if (e.screen < 0 || static_cast<std::size_t>(e.screen) >= touchViews_.size())
    return;
  auto *view = touchViews_[e.screen];
  if (!view || e.type < 0 || e.type > 2)
    return;
  view->receiveTouchInput(Core::Portable::TouchEvent(
      static_cast<Core::Portable::TouchEvent::Type>(e.type),
      Core::Point(e.x, e.y)));
}
} // namespace Presonus
