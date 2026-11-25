#include "presonus/LcdView.hpp"

#include "core/portable/gui/corecontrols.h"

namespace Presonus {
LcdView::LcdView(Core::RectRef size, Core::BitmapPixelFormat pixelFormat,
                 Core::Portable::RootView::RenderMode renderMode)
    : RootView(size, pixelFormat, renderMode) {}

LcdView::~LcdView() {
  if (observer)
    observer->onDestroyed(*this);
}

void LcdView::setFocusView(Core::Portable::View *view) {
  RootView::setFocusView(view);
  if (observer) {
    if (auto *control =
            Core::Portable::core_cast<Core::Portable::Control>(getFocusView()))
      observer->onFocusControlChanged(control);
  }
}
} // namespace Presonus
