#include "presonus/frontier01/frontier01_w03.hpp"
#include <stdexcept>

namespace Presonus {
AllMutesGroup::AllMutesGroup(Mixer::MixerComponentBase &mixer)
    : MuteGroupBase(mixer) {}
AllMutesGroup::~AllMutesGroup() = default;
void AllMutesGroup::activate() {
  if (!mixerData)
    throw std::logic_error("mute mixer data is not bound");
  for (int i = 0; i < mixerData->allMutes.count(); ++i) {
    auto *parameter = mixerData->allMutes[i];
    parameter->setValue(1.f, true);
    state.members.add(parameter);
  }
}
FileMuteGroup::FileMuteGroup(Core::Portable::FileName filename,
                             Core::Portable::Parameter *parameter,
                             Mixer::MixerComponentBase &mixer)
    : MuteGroupBase(mixer), Core::Portable::Component(""), filename_(filename),
      parameter_(parameter) {
  parameter_->addObserver(this);
}
FileMuteGroup::~FileMuteGroup() {
  if (parameter_)
    parameter_->removeObserver(this);
}
void FileMuteGroup::paramChanged(Core::Portable::Parameter *parameter,
                                 int message) {
  if (!parameter_)
    throw std::logic_error("unbound compatibility FileMuteGroup");
  if (message == 3 && reactivate_ && parameter->getValue() == 0.f) {
    parameter->setValue(1.f, false);
    reactivate_ = false;
  }
}
void FileMuteGroup::cacheMutes(const Core::Portable::Attributes &attributes) {
  if (!mixerData)
    throw std::logic_error("mute mixer data is not bound");
  state.members.empty();
  for (int i = 0; i < mixerData->channels.count(); ++i) {
    const auto &channel = mixerData->channels[i];
    const auto *parent = attributes.getAttributes(channel.parentName);
    const auto *child = parent ? parent->getAttributes(channel.name) : nullptr;
    const auto *value =
        child ? child->lookup(channel.mute->getName()) : nullptr;
    if (value && (value->getType() == Core::Portable::AttributeValue::kInt ||
                  value->getType() == Core::Portable::AttributeValue::kFloat)) {
      // Native converts floating attribute payloads to signed int64 before the
      // positivity check. Bounded port domain: finite representable int64.
      const auto positive =
          value->getType() == Core::Portable::AttributeValue::kInt
              ? value->getInt() > 0
              : static_cast<Core::int64>(value->getFloat()) > 0;
      if (positive)
        state.members.add(channel.mute);
    }
  }
  updateStatus();
}

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
