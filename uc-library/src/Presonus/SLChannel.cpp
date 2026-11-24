#include "presonus/SLChannel.hpp"
#include "presonus/MappableMixer.hpp"
#include "presonus/MixerClientComponentBase.hpp"
#include "presonus/color/IColorConverter.hpp"

namespace Presonus {
Core::Portable::Parameter *SLChannelBase::getSelectionParameter() const {
  return nullptr;
}
Core::Portable::Parameter *SLChannelBase::getLinkParameter() const {
  return nullptr;
}
Core::Portable::Parameter *SLChannelBase::getColorParameter() const {
  return nullptr;
}
Core::Portable::Parameter *SLChannelBase::getLinkMasterParameter() const {
  return nullptr;
}
Core::Portable::Parameter *SLChannelBase::getLinkedSelectionParameter() const {
  return nullptr;
}
void SLChannelBase::updateColorIndex() {
  if (!colorMixer_ || !writableColorIndexParameter_)
    return;
  if (const auto *converter = colorMixer_->getColorConverter()) {
    const auto index = converter->getColorIndexForRGB(getColor());
    writableColorIndexParameter_->setValue(static_cast<float>(index), true);
  }
}
void SLChannelBase::updateColorFromIndex() {
  if (!colorMixer_ || !colorIndexParameter_)
    return;
  if (const auto *converter = colorMixer_->getColorConverter()) {
    const auto color = converter->getRGBFromColorIndex(getColorIndex());
    if (auto *parameter = Core::Portable::ColorParam::cast(getColorParameter()))
      parameter->setColor(static_cast<Core::uint32>(color), true);
  }
}
int SLChannelBase::getColorIndex() const {
  return colorIndexParameter_
             ? static_cast<int>(colorIndexParameter_->getValue())
             : 0;
}
Core::Color SLChannelBase::getColor() const {
  const auto *parameter = Core::Portable::ColorParam::cast(getColorParameter());
  return parameter ? Core::Color::fromInt(parameter->getColor())
                   : Core::Color{};
}
int SLChannelBase::getNumber() const {
  const auto *parent = getParent();
  return parent ? parent->getChildIndex(this) + 1 : 0;
}
ChannelType SLChannelBase::getChannelType() const {
  const auto *owner = getParent();
  return sourcePortMixer_ && owner
             ? sourcePortMixer_->getChannelGroupType(*owner)
             : static_cast<ChannelType>(-1);
}
void SLChannelBase::getSlowLinkParams(
    Core::Vector<Core::Portable::Parameter *> &) const {}
Core::Portable::Parameter *SLChannel::getSelectionParameter() const {
  return selection_;
}
Core::Portable::Parameter *SLChannel::getColorParameter() const {
  return color_;
}
Core::Portable::Parameter *SLChannel::getLinkedSelectionParameter() const {
  return linkedSelection_;
}
} // namespace Presonus
