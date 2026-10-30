#include "presonus/surface_panel/BitmapDrawing.hpp"
#include <algorithm>

namespace Presonus::Panel {
int BitmapDisplay::getScreenWidth() const { return 192; }
int BitmapDisplay::getScreenHeight() const { return 64; }

bool BitmapDisplay::getPixel(int x, int y) const {
  const int width = getScreenWidth();
  const int bit = y % 8;
  if (static_cast<unsigned>(bit) > 7)
    return false;
  // Original has no bounds checks. The validated domain requires this offset
  // to be within backing storage, with no signed arithmetic overflow.
  const int offset = (y / 8) * width + x;
  return (bitmap_[offset] & (1U << bit)) != 0;
}

void BitmapDisplay::setPixel(int x, int y, bool value) {
  const int width = getScreenWidth();
  const int bit = y % 8;
  if (static_cast<unsigned>(bit) > 7)
    return;
  const int offset = (y / 8) * width + x;
  const auto mask = static_cast<std::uint8_t>(1U << bit);
  if (value)
    bitmap_[offset] |= mask;
  else
    bitmap_[offset] &= static_cast<std::uint8_t>(~mask);
}

void BitmapDisplay::_fillRect(int x, int y, int width, int height, int mode) {
  x = std::max(x, 0);
  y = std::max(y, 0);
  width = std::max(width, 1);
  height = std::max(height, 1);
  // The domain excludes overflow in these sums, as in the original ARM port.
  if (x + width > getScreenWidth())
    width = getScreenWidth() - x;
  if (y + height > getScreenHeight())
    height = getScreenHeight() - y;
  for (int row = 0; row < height; ++row)
    for (int column = 0; column < width; ++column) {
      const bool value =
          mode == 1 || (mode == 2 && !getPixel(x + column, y + row));
      setPixel(x + column, y + row, value);
    }
}

void BitmapDisplay::_fillRect(const Rectangle &rectangle, int mode) {
  _fillRect(rectangle.x, rectangle.y, rectangle.width, rectangle.height, mode);
}
void BitmapDisplay::fillRect(const Rectangle &rectangle) {
  _fillRect(rectangle, 1);
}
void BitmapDisplay::eraseRect(const Rectangle &rectangle) {
  _fillRect(rectangle, 0);
}
void BitmapDisplay::invertRect(const Rectangle &rectangle) {
  _fillRect(rectangle, 2);
}
int BitmapDisplay::setPen(int pen) {
  const int previous = pen_;
  pen_ = pen;
  return previous;
}
int BitmapDisplay::setTextColor(int color) {
  const int previous = textColor_;
  textColor_ = color;
  return previous;
}
void BitmapDisplay::moveTo(int x, int y) {
  x_ = x;
  y_ = y;
}
void BitmapDisplay::getPos(int &x, int &y) const {
  x = x_;
  y = y_;
}
} // namespace Presonus::Panel
