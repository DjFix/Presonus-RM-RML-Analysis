#include "presonus/surface/DawFxPageComponent.hpp"
#include <bit>
#include <limits>
namespace Presonus::Surface {
DawFxPageComponent::DawFxPageComponent(
    Core::Portable::Parameter *mode, presonus::surface::DawFxBindings bindings,
    int insertOffset, int sendOffset)
    : mode_(mode), bindings_(bindings), insertOffset_(insertOffset),
      sendOffset_(sendOffset) {}
bool DawFxPageComponent::isSendMode() const {
  if (!mode_)
    return false;
  const float value = mode_->getValue();
  // Defined source-port domain: finite values representable as int32.
  return value >= 1.f && value < 2.f;
}
int &DawFxPageComponent::getListOffset() const {
  return isSendMode() ? sendOffset_ : insertOffset_;
}
int DawFxPageComponent::getMaxListOffset() const {
  if (!bindings_.hasFolder(bindings_.context))
    return 0;
  auto n = std::bit_cast<std::int32_t>(
      static_cast<std::uint32_t>(bindings_.usedCount(bindings_.context)) - 1u);
  auto result = (n / 5) * 5;
  return result < 0 ? 0 : result;
}
void DawFxPageComponent::setListOffset(int offset) {
  int &current = getListOffset();
  if (offset < 0)
    offset = 0;
  else {
    int maximum = getMaxListOffset();
    if (offset >= maximum)
      offset = maximum;
  }
  if (current == offset)
    return;
  current = offset;
  bindings_.updateList(bindings_.context, false);
}
void DawFxPageComponent::addListOffset(int delta) {
  auto result = static_cast<std::uint32_t>(getListOffset()) +
                static_cast<std::uint32_t>(delta);
  setListOffset(std::bit_cast<std::int32_t>(result));
}
} // namespace Presonus::Surface
