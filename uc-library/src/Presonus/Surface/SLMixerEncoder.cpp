#include "presonus/surface/sl_mixer_encoder.hpp"
#include <cstdint>
#include <cstring>
namespace Presonus {
void *AssignmentHandler::castTo(int tag) {
  return tag == 0x41734861 ? this : nullptr;
}
void AssignmentHandler::onModifiersChanged() {}
void AssignmentHandler::onIdle() {}
void AssignmentHandler::initialize(Core::Portable::Component *) {}
void AssignmentHandler::setController(IMappingController *p) {
  controller_ = p;
}
void *MixerAssignmentHandler::castTo(int tag) {
  return tag == 0x4d784173 ? this : AssignmentHandler::castTo(tag);
}
void MixerAssignmentHandler::updatePanEncoderConnection() {}
bool MixerAssignmentHandler::handleMappingRadioGroup(
    Core::Portable::Parameter *) {
  return false;
}
void MixerAssignmentHandler::onEncoderChanged(int) {}
bool MixerAssignmentHandler::canActivate() const { return true; }
void MixerAssignmentHandler::handleFootswitch(FootswitchMode, bool) {}
namespace Surface {
Core::Portable::Parameter *SLMixerHandler::getMappingParameter(int tag) const {
  return controller_ ? controller_->getParamByTag(tag) : nullptr;
}
bool SLMixerHandler::altKeyPressed() const {
  auto *parameter = getMappingParameter(11);
  return parameter && parameter->getValue() == 1.f;
}
int SLMixerHandler::getMeterMode() const {
  if (!controller_)
    return 0;
  auto *parameter = controller_->getMainScreenParamByTag(3);
  if (parameter && parameter->getValue() > 0.f)
    return 5;
  const int selected = controller_->getRadioValue(34, 37);
  return selected >= 0 ? selected - 33 : 0;
}
void SLMixerHandler::onEncoderChanged(int index) {
  if (static_cast<std::uint32_t>(index) > 15)
    return;
  if (!encoderTimer_.isExecuting()) {
    savedMeterMode_ = getMeterMode();
    if (savedMeterMode_) {
      // Original ARM ADD wraps modulo32 before mapping dispatch.
      auto raw = static_cast<std::uint32_t>(savedMeterMode_) + 33U;
      int tag;
      std::memcpy(&tag, &raw, 4);
      if (auto *parameter = getMappingParameter(tag))
        parameter->setValue(0.f, true);
    }
  }
  encoderTimer_.beginAction(-1.f);
}
} // namespace Surface
} // namespace Presonus
