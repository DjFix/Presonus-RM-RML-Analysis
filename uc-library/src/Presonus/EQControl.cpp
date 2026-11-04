#include "presonus/mixer_dsp/EQControl.hpp"
#include <stdexcept>
#include <strings.h>

namespace Presonus {
void EQControl::markBandDirty(int index) {
  if (index >= 0 && index < static_cast<int>(portableBands.size()))
    portableBands[static_cast<unsigned>(index)].dirty = true;
}
bool EQControl::isAnyBandOn() const {
  for (const auto &band : portableBands)
    if (band.enabled && band.on)
      return true;
  return false;
}
void EQControl::setBufferedDraw(bool state) {
  if (!drawBoundary)
    throw std::logic_error("EQControl draw boundary must be bound");
  bufferedDraw = state;
  if (!state) {
    if (bufferPresent)
      drawBoundary->releaseBuffer();
    bufferValid = false;
    bufferPresent = false;
  }
  drawBoundary->initBands(*this);
}
float EQControl::getFrequency(int index) const {
  if (index < 0 || index >= static_cast<int>(portableParams.size()))
    return 0.f;
  auto *p = portableParams[static_cast<unsigned>(index)].frequency;
  return p ? p->getValue() : 0.f;
}
float EQControl::getGain(int index) const {
  if (index < 0 || index >= static_cast<int>(portableParams.size()))
    return 0.f;
  auto *p = portableParams[static_cast<unsigned>(index)].gain;
  return p ? p->getValue() : 0.f;
}
float EQControl::getQ(int index) const {
  if (index < 0 || index >= static_cast<int>(portableParams.size()))
    return 0.f;
  auto *p = portableParams[static_cast<unsigned>(index)].q;
  return p ? p->getValue() : 0.f;
}
int EQControl::parseType(Core::ConstString name) {
  if (::strcasecmp(name.str(), "LowShelf") == 0)
    return 1;
  if (::strcasecmp(name.str(), "HighShelf") == 0)
    return 2;
  if (::strcasecmp(name.str(), "LowCut") == 0)
    return 0;
  if (::strcasecmp(name.str(), "Peaking") == 0)
    return 3;
  return 3;
}
void EQControl::addBackgroundPainter(BackgroundPainter &painter) {
  backgroundPainters.add(&painter);
}
int EQControl::freqToX(float frequency) const {
  if (!frequencyNormalizer || !xPixels)
    throw std::logic_error("EQControl frequency providers must be bound");
  return static_cast<int>(xPixels->normalizedToRange(
      frequencyNormalizer->rangeToNormalized(frequency)));
}
int EQControl::gainToY(float gain) const {
  if (!gainNormalizer || !yPixels)
    throw std::logic_error("EQControl gain providers must be bound");
  return static_cast<int>(yPixels->normalizedToRange(
                              1.f - gainNormalizer->rangeToNormalized(gain)) +
                          0.5f);
}
} // namespace Presonus
