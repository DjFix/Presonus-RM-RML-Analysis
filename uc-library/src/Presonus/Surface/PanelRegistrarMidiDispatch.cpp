#include "presonus/surface/MidiMixerHandler.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
namespace Presonus::Surface {
bool PanelRegistrar::addMidiHandler(MidiMixerHandler *handler) {
  return midiHandlers_.add(handler);
}
bool PanelRegistrar::removeMidiHandler(MidiMixerHandler *handler) {
  for (int i = 0; i < midiHandlers_.count(); ++i)
    if (midiHandlers_[i] == handler)
      return midiHandlers_.removeAt(i);
  return false;
}
int PanelRegistrar::countMidiHandlers() const { return midiHandlers_.count(); }
MidiMixerHandler *PanelRegistrar::getMidiHandler(int index) const {
  return midiHandlers_.at(index);
}
void PanelRegistrar::dispatchMidiSwitch(
    const Presonus::Panel::ControlRegistrar &controls, int index, int value,
    bool pressed, Presonus::Panel::SwitchControl *control) {
  for (int i = 0; i < midiHandlers_.count(); ++i)
    if (auto *handler = midiHandlers_[i])
      handler->switchChanged(controls, index, value, pressed, control);
}
void PanelRegistrar::dispatchMidiEncoder(
    const Presonus::Panel::ControlRegistrar &controls, int index, int delta,
    Presonus::Panel::EncoderControl *control) {
  for (int i = 0; i < midiHandlers_.count(); ++i)
    if (auto *handler = midiHandlers_[i])
      handler->encoderChanged(controls, index, delta, control);
}
} // namespace Presonus::Surface
