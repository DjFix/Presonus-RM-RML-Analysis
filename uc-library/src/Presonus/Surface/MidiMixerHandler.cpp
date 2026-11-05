#include "presonus/surface/MidiMixerHandler.hpp"
#include "presonus/MackieControlComponent.hpp"
#include "presonus/MappingTable.hpp"
#include "presonus/panel/switch_control.hpp"
#include <stdexcept>
namespace {
void requireMackie(const presonus::surface::midi_port::State &state) {
  if (!state.normalMackie || !state.alternateMackie)
    throw std::logic_error(
        "MidiMixerHandler requires explicit borrowed Mackie providers");
}
} // namespace
namespace Presonus::Surface {
void MidiMixerHandler::disconnect() {
  requireMackie(state_);
  auto *model = state_.normalMackie->getModel();
  if (model) {
    if (!model->buttonRelease || !model->faderRelease)
      throw std::logic_error("Mackie release operations must be wired");
    model->releaseAllButtons();
  }
  // Resolve the alternate binding after normal releases, preserving mutation.
  requireMackie(state_);
  model = state_.alternateMackie->getModel();
  if (model) {
    if (!model->buttonRelease || !model->faderRelease)
      throw std::logic_error("Mackie release operations must be wired");
    model->releaseAllButtons();
  }
  setControlsEnabled(true);
  resetColors();
  state_.accumulation.fill(0);
}
void MidiMixerHandler::setController(Presonus::IMappingController *controller) {
  state_.controller = controller;
  if (!controller)
    disconnect();
}
void MidiMixerHandler::switchChanged(const Presonus::Panel::ControlRegistrar &,
                                     int, int, bool pressed,
                                     Presonus::Panel::SwitchControl *control) {
  if (!state_.controller)
    return;
  auto *parameter = control->getParameter();
  if (!parameter)
    return;
  auto *original = parameter->getOriginal();
  if (!original)
    return;
  const int tag = original->getTag();
  const bool alternate = original->isUserFlag1();
  requireMackie(state_);
  auto *model =
      (alternate ? state_.alternateMackie : state_.normalMackie)->getModel();
  if (model)
    model->setButtonState(tag, pressed);
}
void MidiMixerHandler::encoderChanged(const Presonus::Panel::ControlRegistrar &,
                                      int index, int delta,
                                      Presonus::Panel::EncoderControl *) {
  if (!state_.controller || static_cast<unsigned>(index) > 16)
    return;
  if (!state_.localParameters)
    throw std::logic_error(
        "MidiMixerHandler requires borrowed local parameters");
  requireMackie(state_);
  auto *parameter = state_.localParameters->getParameterByTag(1);
  // Original boolean __aeabi_fcmpeq result selects 5 for exact +/-0,
  // 15 for unequal (including NaN); a missing parameter retains 5.
  const int divisor = parameter && parameter->getValue() != 0.0f ? 15 : 5;
  const auto bits =
      state_.accumulation[index] + static_cast<std::uint32_t>(delta);
  const std::int64_t sum = bits & 0x80000000u
                               ? static_cast<std::int64_t>(bits) - 0x100000000LL
                               : bits;
  const int quotient = static_cast<int>(sum / divisor);
  state_.accumulation[index] = static_cast<std::uint32_t>(
      sum - static_cast<std::int64_t>(quotient) * divisor);
  if (!quotient)
    return;
  if (index <= 7)
    state_.normalMackie->getModel()->turnEncoder(0x4300 + index, -quotient);
  else if (index <= 15)
    state_.alternateMackie->getModel()->turnEncoder(0x42f8 + index, -quotient);
  else
    state_.normalMackie->getModel()->turnScrubwheel(quotient);
}

void MidiMixerHandler::paramChanged(Core::Portable::Parameter *parameter, int) {
  const int tag = parameter->getTag();
  if (tag == 0) {
    updateRecordReadyMappings();
    return;
  }
  if (tag != 4 && tag != 5 && tag != 0xa007)
    return;
  // Upstream typed casting replaces the original compiler RTTI boundary.
  auto *stringParameter = Core::Portable::StringParam::cast(parameter);
  if (!stringParameter)
    return;
  auto *mode = state_.localParameters->getParameterByTag(5);
  const char *last = ":";
  const char *separator = ":";
  if (mode && mode->getValue() != 0.0f) {
    last = "\'";
    separator = ".";
  }
  // A second live lookup is observable if the first getValue mutates state.
  mode = state_.localParameters->getParameterByTag(5);
  if (mode && mode->getValue() != 0.0f) {
    last = "\'";
    separator = ":";
  }
  auto *output = state_.localParameters->getParameterByTag(2);
  Core::CString256 text = stringParameter->getText();
  text.insert(3, separator);
  text.insert(6, separator);
  text.insert(9, last);
  output->fromString(text.str(), false);
}

void MidiMixerHandler::updateMapping(const MappingItem *items) {
  auto *normal = state_.normalParameters;
  auto *alternate = state_.alternateParameters;
  for (auto *item = items; item->name[0]; ++item) {
    auto *component = item->alternate ? alternate : normal;
    auto *parameter =
        item->tag == 0xffff ? nullptr : component->getParameterByTag(item->tag);
    state_.mappingTable->connect(item->name, parameter, nullptr, false);
    if (item->color)
      state_.mappingTable->setControlColor(item->name, item->color);
    if (item->disable)
      state_.mappingTable->setControlEnabled(item->name, false);
  }
}
bool MidiMixerHandler::getParamFocusInfo(
    Presonus::MixerAssignmentHandler::FocusInfo &,
    Core::Portable::Parameter *) {
  return false;
}
void MidiMixerHandler::connect() { setControlsEnabled(false); }
void MidiMixerHandler::resetColors() {
  for (std::size_t i = 0; i < state_.colorControls.size(); ++i) {
    if (state_.colorControls[i].empty())
      break;
    services_.setDefaultColor(state_.colorControls[i]);
  }
}
const char *MidiMixerHandler::getMappingName(int) {
  return state_.enabled ? "MCU over MIDI" : "";
}
void MidiMixerHandler::resetAccumulation() { state_.accumulation.fill(0); }
void MidiMixerHandler::updateRecordReadyMappings() {
  const bool vpot = services_.recordParameterPresent() &&
                    services_.recordParameterValue() != 0.0f;
  services_.updateRecordMapping(vpot);
}
void MidiMixerHandler::onIdle() {
  if (services_.idleSlotPresent(0))
    services_.invokeIdleSlot(0);
  if (services_.idleSlotPresent(1))
    services_.invokeIdleSlot(1);
}
} // namespace Presonus::Surface
