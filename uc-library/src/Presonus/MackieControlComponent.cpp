#include "presonus/MackieControlComponent.hpp"
#include <cstdint>
#include <cstring>
namespace {
int parameterOffset(int tag, std::uint32_t base) {
  const std::uint32_t bits = static_cast<std::uint32_t>(tag) - base;
  std::int32_t offset;
  static_assert(sizeof(offset) == sizeof(int));
  std::memcpy(&offset, &bits, sizeof(offset));
  return offset;
}
} // namespace
namespace Presonus {
void MackieControlComponent::updateDisplayStyle(int, int, bool) {}
void MackieControlComponent::updateLedColor(int, int) {}

void MackieControlComponent::updateFader(int tag, float value) {
  auto *parameter =
      tag == 0x9000 ? masterFader
                    : faders_.getAt(paramList, parameterOffset(tag, 0x2000));
  if (parameter)
    parameter->setNormalized(value, false);
}
void MackieControlComponent::updateMeter(int tag, float value) {
  if (auto *parameter = meters_.getAt(paramList, tag))
    parameter->setNormalized(value, false);
}
void MackieControlComponent::updateValueBar(int tag, int mode, float value,
                                            bool enabled) {
  const int offset = parameterOffset(tag, 0x4300);
  if (auto *parameter = valueBarModes_.getAt(paramList, offset))
    parameter->setValue(static_cast<float>(mode), false);
  if (auto *parameter = valueBarValues_.getAt(paramList, offset))
    parameter->setNormalized(value, false);
  if (auto *parameter = valueBarFlags_.getAt(paramList, offset))
    parameter->setValue(enabled ? 1.f : 0.f, false);
}
void MackieControlComponent::paramChanged(Core::Portable::Parameter *parameter,
                                          int message) {
  const int tag = parameter->getTag();
  if (tag != 0x9000 && static_cast<std::uint32_t>(tag) - 0x2000u > 7u)
    return;
  switch (message) {
  case 0:
    model.touchFader(tag, true);
    break;
  case 1:
    model.touchFader(tag, false);
    break;
  case 2:
    model.moveFader(tag, parameter->getNormalized());
    break;
  default:
    break;
  }
}

MackieControlComponent::~MackieControlComponent() = default;
void MackieControlComponent::updateLedState(int tag, int state) {
  if (auto *parameter = paramList.byTag(tag))
    parameter->setValue(state == 0 ? 0.f : 1.f, false);
}
void MackieControlComponent::updateTextDisplay(int tag, const char *text, int) {
  if (auto *parameter = paramList.byTag(tag))
    parameter->fromString(text, false);
}
} // namespace Presonus
