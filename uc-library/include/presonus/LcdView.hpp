#pragma once

#include "core/portable/gui/coreview.h"

namespace Core::Portable {
class Control;
}

namespace Presonus {
class LcdView;

class ILcdViewObserver {
public:
  virtual void onFocusControlChanged(Core::Portable::Control *control) = 0;
  virtual void onDestroyed(const LcdView &) {}

protected:
  ~ILcdViewObserver() = default;
};

// Portable source port bound to the pinned Core provider.
class LcdView : public Core::Portable::RootView {
public:
  LcdView(Core::RectRef size, Core::BitmapPixelFormat pixelFormat,
          Core::Portable::RootView::RenderMode renderMode);
  ~LcdView() override;
  void setFocusView(Core::Portable::View *view) override;

  // Independent binding API for the borrowed observer.
  void bindObserver(ILcdViewObserver *value) { observer = value; }

private:
  ILcdViewObserver *observer = nullptr;
};
} // namespace Presonus
