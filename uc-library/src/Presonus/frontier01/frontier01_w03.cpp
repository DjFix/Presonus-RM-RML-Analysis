#include "presonus/frontier01/frontier01_w03.hpp"

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

FocusHelperButton::FocusHelperButton(const Core::TRect<int> &size,
                                     Core::Portable::Parameter *parameter,
                                     int value)
    : Core::Portable::RadioButton(size, parameter, value), active_(false),
      viewName_("") {}

void FocusHelperButton::setAttributes(const Core::Portable::Attributes &a) {
  Core::Portable::RadioButton::setAttributes(a);
  const char *name = a.getString("viewName");
  viewName_ = name ? name : "";
}

bool FileMuteGroup::findAttribute(const Core::Portable::Attributes *attributes,
                                  const char *path, const char *attribute) {
  while (attributes) {
    if (!attributes->lookup(path))
      return attributes->lookup(attribute) != nullptr;
    attributes = attributes->getAttributes(path);
  }
  return false;
}

McuVpotControl::McuVpotControl(const Core::TRect<int> &size,
                               Core::Portable::Parameter *parameter)
    : Core::Portable::Slider(size, parameter), value_(0) {}

McuVpotControl::PortableState McuVpotControl::portableState() const {
  return {image_.getBitmap(), strip_.getBitmap(), slice_.getBitmap(), value_};
}
} // namespace Presonus
