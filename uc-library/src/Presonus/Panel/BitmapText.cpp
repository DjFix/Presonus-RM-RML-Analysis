#include "presonus/surface_panel/BitmapDrawing.hpp"
#include "presonus/surface_panel/TinyFontMetrics.hpp"
#include <algorithm>
#include <cstring>
#include <stdexcept>
namespace {
int wrappedAdd(int a, int b) {
  std::uint32_t bits =
      static_cast<std::uint32_t>(a) + static_cast<std::uint32_t>(b);
  int result;
  static_assert(sizeof(result) == sizeof(bits));
  std::memcpy(&result, &bits, 4);
  return result;
}
} // namespace
namespace Presonus::Panel {
int BitmapDisplay::getCharHeight() const { return 7; }
int BitmapDisplay::getTextBoxHeight() const {
  return wrappedAdd(getCharHeight(), 2);
}
int BitmapDisplay::pixelLength(const char *text) {
  if (!text)
    return 0;
  int length = 0;
  while (static_cast<unsigned char>(text[length]) > 31) {
    if (static_cast<unsigned char>(text[length]) > 126)
      throw std::invalid_argument("valid firmware glyph range required");
    ++length;
  }
  return presonus::surface_panel_port::tinyFontWidth(text, length);
}
void BitmapDisplay::drawString(const char *text, int width, Rectangle *box) {
  drawText(x_, y_, text, width, box);
}
void BitmapDisplay::drawText(int x, int y, const char *text, int maximumWidth,
                             Rectangle *box) {
  if (y < 0)
    return;
  if (wrappedAdd(y, getCharHeight()) >= getScreenHeight() || x < 0)
    return;
  Core::Threads::ScopedLock lock(textLock_);
  if (!text)
    throw std::invalid_argument(
        "nonnull original-memory-valid draw text required");
  std::size_t length = std::strlen(text);
  if (length > 255)
    throw std::invalid_argument("original256-byte text buffer domain");
  char copy[256];
  std::strcpy(copy, text);
  while (maximumWidth > 0 && length > 0 && pixelLength(copy) > maximumWidth)
    copy[--length] = 0;
  const int textWidth = wrappedAdd(pixelLength(copy), 2);
  const int textHeight = getTextBoxHeight();
  if (box) {
    *box = {x - 1, y - 1, textWidth, textHeight};
    const int right = getScreenWidth() - 1, bottom = getScreenHeight() - 1;
    const int left = std::max(box->x, 0);
    const int width = std::min(right, wrappedAdd(box->x, box->width)) - left;
    int top = box->y;
    int height = box->height;
    if (width > 0) {
      const int clippedTop = std::max(box->y, 0);
      height = std::min(bottom, wrappedAdd(box->y, box->height)) - clippedTop;
      if (height > 0) {
        box->x = left;
        top = clippedTop;
      }
    }
    box->y = top;
    box->width = width;
    box->height = height;
    return;
  }
  if (textWidth <= 0 || textHeight <= 0)
    return;
  textDirty_ = true;
  const auto &font = presonus::surface_panel_port::tinyFontBytes();
  int cursor = x;
  for (const unsigned char *p = reinterpret_cast<const unsigned char *>(copy);
       *p > 31; ++p) {
    if (*p > 126)
      throw std::invalid_argument("valid firmware glyph range required");
    const unsigned index = (*p - 32) * 5;
    for (unsigned column = 0; column < 5; ++column) {
      const auto bits = font[index + column];
      if (bits == 251)
        continue;
      if (cursor >= getScreenWidth())
        return;
      for (unsigned bit = 0; bit < 8; ++bit)
        if (bits & (1U << bit))
          setPixel(cursor, y + static_cast<int>(bit), textColor_ != 1);
      ++cursor;
    }
    ++cursor;
  }
  moveTo(cursor, y);
}
} // namespace Presonus::Panel
