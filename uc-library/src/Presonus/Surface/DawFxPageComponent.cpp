#include "presonus/surface/DawFxPageComponent.hpp"
#include "presonus/DAWDeviceFolder.hpp"
#include "presonus/DAWDeviceSlot.hpp"
#include <array>
#include <bit>
#include <cstdio>
#include <cstring>
#include <limits>
namespace Presonus::Surface {
namespace {
using Core::Portable::ParamInfo;

constexpr int modeTag = 1000;
constexpr std::array<ParamInfo, 7> rowParameters{{
    PARAM_STRING(0, "num", 0),
    PARAM_TOGGLE(1, "used", 0, nullptr, 0),
    PARAM_TOGGLE(2, "has-slider", 0, nullptr, 0),
    PARAM_ALIAS(3, "bypass", 0),
    PARAM_ALIAS(4, "name", 0),
    PARAM_ALIAS(5, "edit", 0),
    PARAM_ALIAS(6, "slider", 0),
}};

constexpr ParamInfo controls[] = {
    PARAM_TOGGLE(1001, "page-up", 0, nullptr, 0),
    PARAM_TOGGLE(1003, "page-down", 0, nullptr, 0),
    PARAM_TOGGLE(1002, "one-up", 0, nullptr, 0),
    PARAM_TOGGLE(1004, "one-down", 0, nullptr, 0),
    PARAM_INT(modeTag, "fx-type", 0, 1, 0, nullptr, nullptr, 0, 0),
    PARAM_ALIAS(1005, "bypass-inserts", 0),
};
} // namespace

DawFxPageComponent::DawFxPageComponent(const char *formName, int tag)
    : PageComponent("dawFx", formName, tag) {
  constexpr int rowWidth = static_cast<int>(rowParameters.size());
  for (int row = 0; row < 5; ++row) {
    auto parameters = rowParameters;
    for (int column = 0; column < rowWidth; ++column) {
      auto &parameter = parameters[column];
      parameter.tag += row * rowWidth;
      std::snprintf(parameter.name, sizeof(parameter.name), "%s_%d",
                    rowParameters[column].name, row + 1);
    }
    addParameters(parameters.data(), rowWidth, true);
  }
  addParameters(controls, static_cast<int>(std::size(controls)));
  mode_ = getParameterByTag(modeTag);
}

DawFxPageComponent::DawFxPageComponent(
    Core::Portable::Parameter *mode, presonus::surface::DawFxBindings bindings,
    int insertOffset, int sendOffset)
    : PageComponent("", nullptr, 0), mode_(mode), bindings_(bindings),
      insertOffset_(insertOffset), sendOffset_(sendOffset) {}
void DawFxPageComponent::onWheelInput(const Core::Portable::WheelEvent &event) {
  addListOffset(event.delta);
}
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
int DawFxPageComponent::getEditSlotIndex(DAWDeviceFolder *folder) const {
  if (!folder || std::strcmp(folder->getName(), "inserts") != 0)
    return -1;

  const int used = folder->getUsedCount();
  for (int index = 0; index < used; ++index) {
    const auto *edit = folder->getChild(index)->getParameterByTag(1);
    if (edit && edit->getValue() > 0.f)
      return index;
  }
  return -1;
}
int DawFxPageComponent::calcAutoScroll(DAWDeviceFolder *folder,
                                       DAWDeviceSlot *slot) const {
  const int offset = getListOffset();
  const int index =
      folder && slot ? folder->getChildIndex(slot) : getEditSlotIndex(folder);
  const auto last =
      std::bit_cast<std::int32_t>(static_cast<std::uint32_t>(offset) + 4u);
  if (index < 0 || (index >= offset && index <= last))
    return -1;
  return (index / 5) * 5;
}
int DawFxPageComponent::getMaxListOffset() const {
  if (!bindings_.hasFolder || !bindings_.hasFolder(bindings_.context))
    return 0;
  auto n = std::bit_cast<std::int32_t>(
      static_cast<std::uint32_t>(bindings_.usedCount(bindings_.context)) - 1u);
  auto result = (n / 5) * 5;
  return result < 0 ? 0 : result;
}
void DawFxPageComponent::onFocusChannelChanged() {
  if (bindings_.updateList)
    bindings_.updateList(bindings_.context, true);
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
  if (bindings_.updateList)
    bindings_.updateList(bindings_.context, false);
}
void DawFxPageComponent::addListOffset(int delta) {
  auto result = static_cast<std::uint32_t>(getListOffset()) +
                static_cast<std::uint32_t>(delta);
  setListOffset(std::bit_cast<std::int32_t>(result));
}
} // namespace Presonus::Surface
