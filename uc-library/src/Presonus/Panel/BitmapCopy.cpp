#include "presonus/surface_panel/BitmapDrawing.hpp"
#include <algorithm>
#include <cstring>
namespace {
int wrappingAdd(int a, int b) {
  return static_cast<std::int32_t>(static_cast<std::uint32_t>(a) +
                                   static_cast<std::uint32_t>(b));
}
} // namespace
namespace Presonus::Panel {
char *BitmapDisplay::getBitmapData() const {
  return reinterpret_cast<char *>(const_cast<std::uint8_t *>(bitmap_.data()));
}
void BitmapDisplay::clear() {
  Core::Threads::ScopedLock guard(textLock_);
  std::fill_n(bitmap_.begin(), 1540, pen_ == 1 ? 255 : 0);
  textDirty_ = true;
}
void BitmapDisplay::copyBits(const char *source, const Point &point,
                             const Rectangle &rectangle) {
  copyBits(getBitmapData(), source, point, rectangle);
}
void BitmapDisplay::getScreenBits(char *destination, const Point &point,
                                  const Rectangle &rectangle) {
  copyBits(destination, getBitmapData(), point, rectangle);
}
void BitmapDisplay::copyBits(char *destination, const char *source,
                             const Point &point, const Rectangle &rectangle) {
  const int maxX = getScreenWidth() - 1, maxY = getScreenHeight() - 1;
  int sourceX = rectangle.x, sourceY = rectangle.y;
  int width = std::min(maxX, wrappingAdd(rectangle.x, rectangle.width)) -
              std::max(rectangle.x, 0);
  int height = rectangle.height;
  if (width > 0) {
    height = std::min(maxY, wrappingAdd(rectangle.y, rectangle.height)) -
             std::max(rectangle.y, 0);
    if (height > 0) {
      sourceX = std::max(rectangle.x, 0);
      sourceY = std::max(rectangle.y, 0);
    }
  }
  int destinationWidth =
      std::min(wrappingAdd(width, point.x), maxX) - std::max(point.x, 0);
  if (destinationWidth > 0)
    height =
        std::min(wrappingAdd(height, point.y), maxY) - std::max(point.y, 0);
  for (int y = 0; y < height; ++y)
    for (int x = 0; x < destinationWidth; ++x) {
      int sourceRow = sourceY + y, destinationRow = point.y + y;
      unsigned char sourceMask = 1u << (sourceRow & 7),
                    destinationMask = 1u << (destinationRow & 7);
      bool value = false;
      if (source && static_cast<unsigned>(sourceRow % 8) <= 7)
        value = (static_cast<unsigned char>(
                     source[(sourceRow / 8) * getScreenWidth() + sourceX + x]) &
                 sourceMask) != 0;
      if (destination && static_cast<unsigned>(destinationRow % 8) <= 7) {
        auto &byte =
            destination[(destinationRow / 8) * getScreenWidth() + point.x + x];
        byte = static_cast<char>(
            value ? (static_cast<unsigned char>(byte) | destinationMask)
                  : (static_cast<unsigned char>(byte) &
                     static_cast<unsigned char>(~destinationMask)));
      }
    }
  if (destination == getBitmapData())
    textDirty_ = true;
}
} // namespace Presonus::Panel
