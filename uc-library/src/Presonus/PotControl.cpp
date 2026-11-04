#include "presonus/PotControl.hpp"

namespace Presonus {
namespace {
// Exact names and bit values from the selected ELF's 24-byte option table.
const Core::EnumInfo potOptions[] = {
    {"textinput", 0x200000}, {"onoffmode", 0x400000}, {nullptr, 0}};
} // namespace

PotControl::PotControl(const Core::TRect<int> &size)
    : Core::Portable::Control(size, nullptr), focusMode_(0), previousValue_(-1),
      frameCount_(0) {
  options |= 0x14;
}

// Explicit source adaptation audited against actual PotControl D1 at0x69c88
// (SHA e620c3602b32ba075e64e224b99af4d21a507f01f9ed22509c83242e83cd66c7):
// actual CCL unuse in slice/strip/image order, then Control teardown.
PotControl::~PotControl() {
  focusSlice_.assign(nullptr);
  focusStrip_.assign(nullptr);
  image_.assign(nullptr);
}

void PotControl::setFrame(int frame) {
  const bool changed = frame != previousValue_;
  previousValue_ = frame;
  if (changed)
    invalidate();
}

void PotControl::changeFrames() {
  auto *parameter = getParameter();
  if (!parameter) {
    setFrame(0);
    return;
  }
  const float value = parameter->getNormalized();
  if (options & 0x400000)
    setFrame(value > 0.01f ? frameCount_ - 1 : 0);
  else
    setFrame(static_cast<int>(value * static_cast<float>(frameCount_ - 1)));
}
void PotControl::draw(const Core::Portable::DrawEvent &event) {
  if (previousValue_ < 0)
    changeFrames();
  auto *bitmap = (focusMode_ == 2 && (options & 8)) ? focusStrip_.getBitmap()
                                                    : image_.getBitmap();
  const auto drawFrame = [&](Core::Portable::Bitmap *image) {
    Core::TRect<int> source(0, 0, image->getWidth(), image->getHeight());
    if (image->getFrameCount() > 1) {
      const int height = image->getHeight() / image->getFrameCount();
      source.top = previousValue_ * height;
      source.bottom = source.top + height;
    }
    event.graphics.drawBitmap(Core::TPoint<int>(0, 0), *image, source);
  };
  if (bitmap && previousValue_ >= 0 && previousValue_ < frameCount_)
    drawFrame(bitmap);
  if (options & 8) {
    if (focusMode_ == 0)
      drawFocusFrame(event);
    else if (focusMode_ == 1)
      drawFrame(focusSlice_.getBitmap());
  }
}

void PotControl::setAttributes(const Core::Portable::Attributes &a) {
  Core::Portable::View::setAttributes(a);
  options |=
      Core::Portable::ViewAttributes::getOptions(a, potOptions, "options");
  image_ = Core::Portable::ViewAttributes::getBitmap(a, "image");
  if (image_.isValid())
    frameCount_ = image_.getBitmap()->getFrameCount();
  focusSlice_ = Core::Portable::ViewAttributes::getBitmap(a, "focusSlice");
  focusStrip_ = Core::Portable::ViewAttributes::getBitmap(a, "focusStrip");
  focusMode_ = focusSlice_.isValid() ? 1 : (focusStrip_.isValid() ? 2 : 0);
  if (options & 0x400000)
    options &= ~4;
}

PotControl::PortableState PotControl::portableState() const {
  return {image_.getBitmap(),
          focusStrip_.getBitmap(),
          focusSlice_.getBitmap(),
          focusMode_,
          previousValue_,
          frameCount_,
          options};
}
} // namespace Presonus
