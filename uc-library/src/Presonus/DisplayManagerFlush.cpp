#include "core/system/corethread.h"
#include "presonus/surface/DisplayManager.hpp"
#include <algorithm>
namespace Presonus {
void DisplayManager::flushColorLcdUpdates() {
  if (suspended_ || root_->getDirtyRegion().getRects().isEmpty())
    return;
  if (root_->getRenderMode() == Core::Portable::RootViewBase::kFlipMode) {
    while (port_->isDisplayBufferActive(root_->getNextRenderBuffer()))
      Core::Threads::CurrentThread::sleep(1);
  }
  const auto &rects = root_->getDirtyRegion().getRects();
  std::uint16_t x = 32767, y = 32767, width = 2, height = 2;
  if (!rects.isEmpty()) {
    int left = 32767, top = 32767, right = -32767, bottom = -32767;
    for (int i = 0; i < rects.count(); ++i) {
      const auto &r = rects[i];
      left = std::min(left, r.left);
      top = std::min(top, r.top);
      right = std::max(right, r.right);
      bottom = std::max(bottom, r.bottom);
    }
    x = static_cast<std::uint16_t>(left);
    y = static_cast<std::uint16_t>(top);
    width = static_cast<std::uint16_t>(right - x);
    height = static_cast<std::uint16_t>(bottom - y);
  }
  root_->redraw();
  DisplayUpdate update{0, root_->accessForRead(), x, y, width, height};
  port_->updateDisplay(update);
}
} // namespace Presonus
