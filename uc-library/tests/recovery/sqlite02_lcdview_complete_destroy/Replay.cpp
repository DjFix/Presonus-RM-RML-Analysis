#include "core/portable/gui/corecontrols.h"
#include "presonus/LcdView.hpp"

#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string>
#include <string_view>

using namespace Core;
using namespace Core::Portable;
using namespace Presonus;
static void *tracked = nullptr;
static bool freed = false;
static const void *bitmap = nullptr;
static bool bitmapFreed = false;

void operator delete(void *pointer) noexcept {
  if (tracked && pointer == tracked)
    freed = true;
  if (bitmap && pointer == bitmap)
    bitmapFreed = true;
  std::free(pointer);
}

void operator delete(void *pointer, std::size_t) noexcept {
  ::operator delete(pointer);
}

struct Observer : ILcdViewObserver {
  LcdView *view = nullptr;
  Control *control = nullptr;
  int focus = 0;
  int destroyed = 0;

  void onFocusControlChanged(Control *current) override {
    if (current != control || view->getFocusView() != current)
      std::abort();
    ++focus;
  }

  void onDestroyed(const LcdView &current) override {
    if (&current != view || freed || bitmapFreed)
      std::abort();
    ++destroyed;
  }
};

struct DerivedView : LcdView {
  using LcdView::LcdView;
};

int main(int argc, char **argv) {
  if (argc != 9)
    return 2;
  std::string_view variant(argv[1]);
  const bool observed = std::atoi(argv[2]);
  const int width = std::atoi(argv[3]);
  const int height = std::atoi(argv[4]);
  auto format = static_cast<BitmapPixelFormat>(std::atoi(argv[5]));
  auto mode = static_cast<RootView::RenderMode>(std::atoi(argv[6]));
  int focusCase = std::atoi(argv[7]);
  const bool repeat = std::atoi(argv[8]);
  const Rect size(0, 0, width, height);
  Observer observer;
  View plain(size);
  Control control(size);
  observer.control = &control;

  alignas(DerivedView) unsigned char storage[sizeof(DerivedView)];
  LcdView *view = nullptr;
  if (variant == "base_construct" || variant == "base_destroy")
    view = new (storage) DerivedView(size, format, mode);
  else if (variant == "deleting_destroy")
    view = new LcdView(size, format, mode);
  else
    view = new (storage) LcdView(size, format, mode);
  observer.view = view;
  if (observed)
    view->bindObserver(&observer);
  if (view->getSize() != size || view->getFormat() != format ||
      view->getRenderMode() != mode || view->getFocusView())
    return 3;

  if (variant == "set_focus_view") {
    View *request = focusCase == 1   ? &plain
                    : focusCase == 2 ? &control
                                     : nullptr;
    if (repeat)
      view->RootView::setFocusView(request);
    view->setFocusView(request);
    if (view->getFocusView() != request)
      return 4;
    view->bindObserver(nullptr);
  }

  bitmap = view->getActiveBufferBitmap();
  if (variant == "deleting_destroy") {
    tracked = view;
    RootView *root = view;
    delete root;
  } else if (variant == "base_destroy" || variant == "base_construct") {
    static_cast<DerivedView *>(view)->~DerivedView();
  } else {
    view->~LcdView();
  }

  if (bitmap && !bitmapFreed)
    return 5;
  std::cout << observer.focus << ' ' << observer.destroyed << ' ' << freed
            << '\n';
}
