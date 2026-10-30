#include "presonus/surface_panel/BitmapDrawing.hpp"
#include <algorithm>
namespace Presonus::Panel {
BitmapDisplay::BitmapDisplay() {
  pen_ = 0;
  textColor_ = 0;
  x_ = 0;
  y_ = 0;
  textDirty_ = true;
  port_ = nullptr;
  std::fill_n(bitmap_.begin(), 1540, 0);
  lastSent_.fill(255);
}
BitmapDisplay::~BitmapDisplay() =
    default; // Real lock and actual CCL Singleton base cleanup.
} // namespace Presonus::Panel
DEFINE_SINGLETON(Presonus::Panel::BitmapDisplay)
