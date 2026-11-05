#include "presonus/mixer_dsp/Dsp.hpp"
#include "presonus/mixer_dsp/EQControl.hpp"
#include <bit>
#include <cstring>
#include <initializer_list>
#include <stdexcept>
namespace Presonus {
bool EQControl::BandParams::contains(Core::Portable::Parameter *p) const {
  return gain == p || q == p || frequency == p || slot3 == p || slot4 == p ||
         slot5 == p;
}
void EQControl::BandParams::zeroParam(Core::Portable::Parameter *p) {
  // Native is a first-match operation and deliberately does not clear slot5.
  if (gain == p)
    gain = nullptr;
  else if (q == p)
    q = nullptr;
  else if (frequency == p)
    frequency = nullptr;
  else if (slot3 == p)
    slot3 = nullptr;
  else if (slot4 == p)
    slot4 = nullptr;
}
// Native observer order is raw slots 0,3,1,2,4,5. In the semantic
// portable model slot3 carries type, while frequency carries native slot3.
void EQControl::BandParams::removeObserver(EQControl *owner) {
  auto *observer = owner ? owner->portableObserver() : nullptr;
  for (auto *parameter : {slot3, frequency, gain, q, slot4, slot5})
    if (parameter)
      parameter->removeObserver(observer);
}
void EQControl::BandParams::addObserver(EQControl *owner) {
  auto *observer = owner ? owner->portableObserver() : nullptr;
  for (auto *parameter : {slot3, frequency, gain, q, slot4, slot5})
    if (parameter)
      parameter->addObserver(observer);
}
void EQControl::setBand(int index, BandParams parameters) {
  if (index < 0 || index >= static_cast<int>(portableBands.size()))
    return;
  const auto i = static_cast<unsigned>(index);
  if (portableParams.size() < portableBands.size() ||
      typeParameters.size() < portableBands.size())
    throw std::logic_error("EQControl setBand bindings must cover bands");
  auto old = portableParams[i];
  old.slot3 = typeParameters[i];
  old.removeObserver(this);
  portableParams[i] = parameters;
  typeParameters[i] = parameters.slot3;
  portableParams[i].addObserver(this);
  portableBands[i].dirty = 1;
}
bool EQControl::isBufferedDraw() const { return bufferedDraw; }
} // namespace Presonus
