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
int EQControl::toXGridPixel(float frequency) const {
  return freqToX(frequency);
}
int EQControl::toYGridPixel(float gain) const { return gainToY(gain); }
int EQControl::getType(int index) const {
  if (index < 0 || index >= static_cast<int>(typeParameters.size()))
    return 0;
  auto *parameter = typeParameters[static_cast<unsigned>(index)];
  return parameter ? static_cast<int>(parameter->getValue()) : 0;
}
bool EQControl::getBandEnabled(int index) const {
  if (index < 0 || index >= static_cast<int>(portableParams.size()))
    return false;
  auto *parameter = portableParams[static_cast<unsigned>(index)].slot4;
  return parameter && parameter->getValue() > parameter->getMin();
}
int EQControl::getBandForPoint(const Core::TPoint<int> &point) const {
  if (portableBands.empty())
    return -1;
  if (!portableView)
    throw std::logic_error("EQControl view provider must be bound");
  if (portableParams.size() < portableBands.size())
    throw std::logic_error(
        "EQControl band parameter bindings must cover bands");
  Core::Rect rectangle;
  portableView->getClientRect(rectangle);
  Core::Vector<SortedBand> sorted;
  for (int i = 0; i < static_cast<int>(portableBands.size()); ++i) {
    const auto &band = portableBands[static_cast<unsigned>(i)];
    if (!band.enabled || !portableParams[static_cast<unsigned>(i)].slot5)
      continue;
    SortedBand candidate;
    candidate.index = i;
    candidate.x = freqToX(band.frequency);
    int insertion = 0;
    while (insertion < sorted.count() && candidate.x >= sorted.at(insertion).x)
      ++insertion;
    if (!sorted.insertAt(insertion, candidate))
      throw std::bad_alloc();
  }
  if (!sorted.count())
    return -1;
  // Native single-candidate fast path returns zero, even for a different
  // original band index and points outside the client rectangle.
  if (sorted.count() == 1)
    return 0;
  sorted.at(0).left = 0;
  sorted.at(sorted.count() - 1).right = rectangle.right;
  for (int i = 0; i + 1 < sorted.count(); ++i) {
    int midpoint = sorted.at(i).x + (sorted.at(i + 1).x - sorted.at(i).x) / 2;
    sorted.at(i).right = midpoint;
    sorted.at(i + 1).left = midpoint;
  }
  for (const auto &candidate : sorted)
    if (point.x >= candidate.left && point.x < candidate.right &&
        point.y >= rectangle.top && point.y < rectangle.bottom)
      return candidate.index;
  return -1;
}
bool EQControl::onTouchInput(const Core::Portable::TouchEvent &event) {
  if (!primaryParameter)
    return false;
  if (event.type != Core::Portable::TouchEvent::kDown)
    return true;
  int index = getBandForPoint(event.where);
  if (index >= 0 && index < static_cast<int>(portableParams.size())) {
    auto &parameters = portableParams[static_cast<unsigned>(index)];
    if (parameters.slot4)
      parameters.slot4->setValue(1.f, true);
    if (parameters.slot5)
      parameters.slot5->setValue(1.f, true);
  }
  return true;
}
void EQControl::initBands() {
  if (!portableView)
    throw std::logic_error("EQControl view provider must be bound");
  Core::Rect rectangle;
  portableView->getClientRect(rectangle);
  int width = rectangle.getWidth(), height = rectangle.getHeight();
  if (width <= 0 || height <= 0)
    return;
  // Native tears down and recreates all per-band curve objects. The band
  // parameter vector retains existing elements; RAII is an intentional port.
  bandCurves = std::vector<std::vector<float>>(
      portableBands.size(),
      std::vector<float>(static_cast<unsigned>(width), 0.f));
  for (auto &band : portableBands) {
    band = PortableBand{};
    band.dirty = 1;
  }
  portableParams.resize(portableBands.size());
  amplitudeCurve.assign(static_cast<unsigned>(width), 0.f);
  if (bufferedDraw) {
    pixelCurve.clear();
    bitmap = std::make_unique<Core::Portable::Bitmap>(width, height,
                                                      Core::kBitmapRGBAlpha, 0);
    bitmap->setAlphaChannelUsed(true);
    bufferPresent = true;
    bufferValid = true;
  } else {
    pixelCurve.assign(static_cast<unsigned>(width), 0);
  }
}
void EQControl::drawCurve(const Core::Portable::DrawEvent &event,
                          const Core::Color &color, bool) {
  if (!isAnyBandOn())
    return;
  if (!portableView)
    throw std::logic_error("EQControl view provider must be bound");
  Core::Rect rectangle;
  portableView->getClientRect(rectangle);
  int width = rectangle.getWidth();
  if (width <= 1)
    return;
  if ((bufferedDraw ? amplitudeCurve.size() : pixelCurve.size()) <
      static_cast<unsigned>(width))
    throw std::logic_error("EQControl curve storage must cover view width");
  for (int x = 0; x < width - 1; ++x) {
    int y0 = bufferedDraw ? gainToY(amplitudeCurve[static_cast<unsigned>(x)])
                          : pixelCurve[static_cast<unsigned>(x)];
    int y1 = bufferedDraw
                 ? gainToY(amplitudeCurve[static_cast<unsigned>(x + 1)])
                 : pixelCurve[static_cast<unsigned>(x + 1)];
    Core::Point first(x, y0), second(x + 1, y1);
    if (event.updateRect.pointInside(first) ||
        event.updateRect.pointInside(second))
      event.graphics.drawLine(first, second, color);
  }
}
void EQControl::paramChanged(Core::Portable::Parameter *parameter,
                             int message) {
  if (!observerControl)
    throw std::logic_error("EQControl control observer provider must be bound");
  if (portableParams.size() < portableBands.size() ||
      typeParameters.size() < portableBands.size())
    throw std::logic_error("EQControl observer bindings must cover bands");
  if (message == Core::Portable::Parameter::kChanged ||
      (message == Core::Portable::Parameter::kDestroyed &&
       parameter != primaryParameter)) {
    for (unsigned i = 0; i < portableBands.size(); ++i) {
      auto &parameters = portableParams[i];
      // Explicit conversion to the helper's positional six-slot domain.
      // Existing semantic gain/Q/frequency fields retain their meaning.
      BandParams nativeSlots{typeParameters[i], parameters.gain,
                             parameters.q,      parameters.frequency,
                             parameters.slot4,  parameters.slot5};
      if (!nativeSlots.contains(parameter))
        continue;
      if (message == Core::Portable::Parameter::kChanged)
        portableBands[i].dirty = 1;
      else {
        nativeSlots.zeroParam(parameter);
        typeParameters[i] = nativeSlots.gain;
        parameters.gain = nativeSlots.q;
        parameters.q = nativeSlots.frequency;
        parameters.frequency = nativeSlots.slot3;
        parameters.slot4 = nativeSlots.slot4;
        parameters.slot5 = nativeSlots.slot5;
        portableBands[i].enabled = false;
        parameter->removeObserver(&observer);
      }
      break;
    }
  }
  observerControl->Core::Portable::Control::paramChanged(parameter, message);
}
} // namespace Presonus
