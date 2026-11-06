#include "core/portable/gui/corefont.h"
#include "core/portable/gui/coregraphics.h"
#include "core/public/corestringbuffer.h"
#include "presonus/GridPainter.hpp"
#include <algorithm>
#include <stdexcept>
namespace Presonus {
void GridPainter::paint(const Core::TRect<int> &rectangle,
                        const Core::Portable::DrawEvent &event,
                        const Core::Portable::Style &style) {
  if (!cached_)
    BackgroundPainter::paint(rectangle, event, style);
  if (rectangle_ != rectangle) {
    rectangle_ = rectangle;
    if (cached_) {
      bitmap_.reset();
      // Original requests RGB565. Modern ColorBitmapRenderer rejects a source
      // bitmap whose format differs from its RGBA destination. The cache uses
      // RGBA as an intentional source port, without native RGB565 quantization.
      if (rectangle.getWidth() <= 0 || rectangle.getHeight() <= 0)
        throw std::invalid_argument("GridPainter requires positive cache size");
      bitmap_ = std::make_unique<Core::Portable::Bitmap>(
          rectangle.getWidth(), rectangle.getHeight(), Core::kBitmapRGBAlpha);
      bitmap_->setAlphaChannelUsed(false);
      Core::Portable::ColorBitmapRenderer graphics(*bitmap_);
      graphics.fillRect(rectangle_, style.getBackColor());
      Core::Rect update(0, 0, rectangle.getWidth(), rectangle.getHeight());
      Core::Portable::DrawEvent cachedEvent(graphics, update, Core::Point());
      paintGrid(rectangle_, rectangle_, cachedEvent, style);
    }
  }
  if (!cached_) {
    paintGrid(rectangle, event.updateRect, event, style);
  } else {
    if (!bitmap_)
      throw std::logic_error(
          "GridPainter cache requires a nonzero first rectangle");
    Core::Rect source = bitmap_->getSize();
    source.bound(event.updateRect);
    event.graphics.drawBitmap(event.updateRect.getLeftTop(), *bitmap_, source);
  }
}
void GridPainter::paintGrid(const Core::TRect<int> &,
                            const Core::TRect<int> &clip,
                            const Core::Portable::DrawEvent &event,
                            const Core::Portable::Style &style) {
  auto color = style.getBackColor();
  color.red = std::min(255, int(color.red) + 51);
  color.green = std::min(255, int(color.green) + 51);
  color.blue = std::min(255, int(color.blue) + 51);
  const int width = rectangle_.getWidth(), height = rectangle_.getHeight();
  auto &graphics = event.graphics;
  const auto *font = graphics.getFont(style.getFontName());
  const int lineHeight = font ? font->getLineHeight() : height;
  auto textFor = [&](float value, const Core::Formatter *formatter) {
    Core::CString32 text;
    if (formatter) {
      Core::Formatter::Data data{this, text.getBuffer(), 32, value, nullptr};
      formatter->print(data);
    } else {
      text.appendFormat("%d", static_cast<int>(value));
    }
    return text;
  };
  if ((!xValues_.isEmpty() || !yValues_.isEmpty()) && !provider_)
    throw std::logic_error("GridPainter requires a grid provider");
  for (int i = 0; i < xValues_.count(); ++i) {
    const float value = xValues_[i];
    const int x = provider_->toXGridPixel(value);
    if (x >= clip.left && x <= clip.right)
      graphics.drawLine(Core::Point(x, 0), Core::Point(x, height), color);
    if (!font || !labels_ || first_.orientation < 1 || first_.orientation > 2)
      continue;
    const auto text = textFor(value, first_.formatter);
    const int textWidth = font->getStringWidth(text, text.length());
    Core::Rect label(x - textWidth / 2, 0, x - textWidth / 2 + textWidth,
                     lineHeight);
    if (label.left < 0 || label.right > width)
      continue;
    if (first_.orientation == 2) {
      label.top = height - lineHeight;
      label.bottom = height;
    }
    Core::Rect intersection(label);
    if (!intersection.bound(clip))
      continue;
    graphics.fillRect(label, style.getBackColor());
    graphics.drawString(label, text, style.getForeColor(), style.getFontName(),
                        1);
  }
  for (int i = 0; i < yValues_.count(); ++i) {
    const float value = yValues_[i];
    const int y = provider_->toYGridPixel(value);
    // Preserve original bge/bgt condition, even for coordinates outside clip.
    if (y >= clip.top || y <= clip.bottom)
      graphics.drawLine(Core::Point(0, y), Core::Point(width, y), color);
    if (!font || !labels_ || second_.orientation < 3 || second_.orientation > 4)
      continue;
    const auto text = textFor(value, second_.formatter);
    const int textWidth = font->getStringWidth(text, text.length());
    Core::Rect label(0, y - lineHeight / 2, textWidth,
                     y - lineHeight / 2 + lineHeight);
    if (label.top < 0 || label.bottom > height)
      continue;
    if (second_.orientation == 4) {
      label.left = width - textWidth;
      label.right = width;
    }
    Core::Rect intersection(label);
    // Native Y label intersection uses event.updateRect, unlike X labels.
    if (!intersection.bound(event.updateRect))
      continue;
    graphics.fillRect(label, style.getBackColor());
    graphics.drawString(label, text, style.getForeColor(), style.getFontName(),
                        1);
  }
}
} // namespace Presonus
