#include "presonus/mixer_dsp/EQControl.hpp"
#include "core/system/coretime.h"
#include "presonus/dsp/biquad_calc.hpp"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <stdexcept>
#include <strings.h>

namespace presonus::dsp {
EQControlFrequencyInterpolator::EQControlFrequencyInterpolator()
    : Core::Interpolator(0.f, 1.f) {}
void EQControlFrequencyInterpolator::setRange(float minimum, float maximum,
                                              float midpoint) {
  configured = false;
  if (minimum == 0.f && maximum == 1.f &&
      (midpoint == 0.f || midpoint == 1.f)) {
    Core::Interpolator::setRange(minimum, maximum, midpoint);
    return;
  }
  positiveRange.setRange(minimum, maximum, midpoint);
  Core::Interpolator::setRange(minimum, maximum, midpoint);
  configured = true;
}
float EQControlFrequencyInterpolator::normalizedToRange(float value) const {
  if (!configured)
    throw std::domain_error(
        "EQControl frequency bootstrap requires a supported positive range");
  return positiveRange.normalizedToRange(value);
}
float EQControlFrequencyInterpolator::rangeToNormalized(float value) const {
  if (!configured)
    throw std::domain_error(
        "EQControl frequency bootstrap requires a supported positive range");
  return positiveRange.rangeToNormalized(value);
}
} // namespace presonus::dsp
namespace Presonus {
namespace {
// Source initializers decoded from the hash-bound original HPF table. Host
// pointers and layout belong to the pinned CCL release, never copied ARM bytes.
const Core::Portable::ParamInfo hpfParamInfo[] = {
    {Core::Portable::ParamInfo::kFloat, 0, "hpfQ", .7f, .7f, .7f, .7f, .002f, 0,
     "", "skew", nullptr, nullptr, nullptr},
    {Core::Portable::ParamInfo::kFloat, 1, "hpfGain", 0.f, 0.f, 0.f, 0.f, .002f,
     0, "gain", "linear", nullptr, nullptr, nullptr},
    {Core::Portable::ParamInfo::kInt, 2, "hpfType", 0.f, 0.f, 0.f, 0.f, 1.f, 0,
     "", "", nullptr, nullptr, nullptr}};
} // namespace
EQControl::PortableConstructorState::PortableConstructorState(
    const Core::Rect &rectangle)
    : control(rectangle, nullptr), hpfInfo(hpfParamInfo) {
  // CCL's TViewBase initializes options to zero (including focus).
  control.wantsTouch(true);
  hpfParameters.add(hpfInfo, 3, false);
}
EQControl::EQControl(const Core::TRect<int> &rectangle)
    : constructorState(std::make_unique<PortableConstructorState>(rectangle)),
      observer(*this) {
  portableView = &constructorState->control;
  observerControl = &constructorState->control;
  bindPortableInterpolators(constructorState->frequency, constructorState->x,
                            constructorState->gain, constructorState->y);
  // The partial-object tag intentionally retains its historical 20..20000
  // defaults. Original getCurve reads independent offsets0x88/0x8c, both
  // constructor-initialized zero; these are not frequency-provider range(0,1).
  curveMinimum = 0.f;
  curveMaximum = 0.f;
}

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
void EQControl::setNumBands(int count) {
  requestedBandCount = count;
  // Native negative allocation behavior is excluded. Retain the requested
  // signed count and represent its empty iteration domain without allocation.
  portableBands.resize(static_cast<unsigned>(std::max(count, 0)));
  initBands();
}
void EQControl::setSize(const Core::TRect<int> &rectangle) {
  if (!portableView)
    throw std::logic_error("EQControl view provider must be bound");
  portableView->setSize(rectangle);
  initBands();
}
bool EQControl::getCurve(float *destination, int index, int samples) const {
  if (index < 0 || index >= static_cast<int>(portableBands.size()) ||
      index >= static_cast<int>(typeParameters.size()) ||
      !typeParameters[static_cast<unsigned>(index)] || curveMinimum == 0.f ||
      curveMaximum == 0.f || samples == 0)
    return false;
  const float q = getQ(index);
  if (q == 0.f)
    return false;
  if (samples > 0 && !destination)
    throw std::invalid_argument("EQControl curve destination must be valid");
  const int type = getType(index);
  // Negative type indexing is unchecked in the original; exclude it explicitly.
  if (type < 0)
    throw std::out_of_range("EQControl negative filter type is unsupported");
  const int modes[] = {3, 8, 9, 6};
  const int mode = type <= 3 ? modes[type] : 6;
  presonus::dsp::BiquadState<float> seed{};
  seed.mode = 6;
  seed.word54 = 1;
  seed.frequency = 1000.f;
  seed.q = 0.7f;
  seed.coefficients[0] = 1.f;
  DSP::BiquadCalc<float, false> calculator(presonus::dsp::BiquadSeedTag{},
                                           seed);
  calculator.setup(32, 88200.);
  calculator.setParams(mode, getFrequency(index), q, getGain(index));
  const auto &state = calculator.portableState();
  const auto &c = state.coefficients;
  const float b1 = c[2] / c[0], b2 = c[4] / c[0];
  const float a1 = -c[1], a2 = -c[3];
  const float step = static_cast<float>(
      std::pow(static_cast<double>(curveMaximum / curveMinimum),
               static_cast<double>(1.f / static_cast<float>(samples))));
  float scale = 1.f;
  switch (state.word54) {
  case 2:
  case 4:
    scale = 2.f;
    break;
  case 3:
  case 5:
    scale = 3.f;
    break;
  case 6:
    scale = 4.f;
    break;
  }
  // Native two-iteration reciprocal-root estimate, retaining binary32 staging.
  const auto magnitude = [](float squared) {
    if (squared == 0.f)
      return 0.f;
    std::uint32_t bits;
    std::memcpy(&bits, &squared, sizeof bits);
    bits = 0x5f3759dfu - (bits >> 1);
    float inverse;
    std::memcpy(&inverse, &bits, sizeof inverse);
    const float half = squared * 0.5f;
    inverse = inverse * (1.5f - inverse * (half * inverse));
    inverse = inverse * (1.5f - inverse * (half * inverse));
    return squared * inverse;
  };
  float frequency = curveMinimum;
  for (int x = 0; x < samples; ++x) {
    const float angle = static_cast<float>(
        (static_cast<double>(frequency) + static_cast<double>(frequency)) *
        static_cast<double>(state.piOverRate));
    const float cosine = std::cos(angle), sine = std::sin(angle);
    const float real2 = cosine * cosine - sine * sine;
    const float imaginary2 = sine * (cosine + cosine);
    const float numeratorReal = b2 + (real2 + b1 * cosine);
    const float numeratorImaginary = imaginary2 + b1 * sine;
    const float denominatorReal = a2 + (real2 + a1 * cosine);
    const float denominatorImaginary = imaginary2 + a1 * sine;
    const float numerator = magnitude(numeratorReal * numeratorReal +
                                      numeratorImaginary * numeratorImaginary);
    const float denominator =
        magnitude(denominatorReal * denominatorReal +
                  denominatorImaginary * denominatorImaginary);
    const float ratio = (c[0] * numerator) / denominator;
    const float decibels =
        ratio < 0x1.0efe7ep-24f ? -144.f : std::log10(ratio) * 20.f;
    destination[x] = scale * decibels;
    frequency = frequency * step;
  }
  return true;
}
void EQControl::rebuildCurves() {
  if (!portableView)
    throw std::logic_error("EQControl view provider must be bound");
  Core::Rect rectangle;
  portableView->getClientRect(rectangle);
  const int width = rectangle.getWidth();
  if (width <= 0 || portableBands.empty())
    return;
  if (bandCurves.size() < portableBands.size() ||
      amplitudeCurve.size() < static_cast<unsigned>(width) ||
      (!bufferedDraw && pixelCurve.size() < static_cast<unsigned>(width)))
    throw std::logic_error("EQControl curve storage must cover view and bands");
  bool changed = false;
  for (unsigned i = 0; i < portableBands.size(); ++i) {
    auto &band = portableBands[i];
    if (!band.dirty)
      continue;
    auto &curve = bandCurves[i];
    if (curve.size() < static_cast<unsigned>(width))
      throw std::logic_error("EQControl band curve must cover view width");
    band.on = getBandEnabled(static_cast<int>(i));
    band.gain = getGain(static_cast<int>(i));
    band.frequency = getFrequency(static_cast<int>(i));
    getCurve(curve.data(), static_cast<int>(i), width);
    // Original tests the allocated pointer, not getCurve's result.
    band.enabled = curve.data() != nullptr;
    band.dirty = 0;
    band.x = freqToX(band.frequency);
    band.y = gainToY(band.gain);
    changed = true;
  }
  if (!changed)
    return;
  std::fill_n(amplitudeCurve.begin(), width, 0.f);
  if (!bufferedDraw)
    std::fill_n(pixelCurve.begin(), width, 0);
  for (int x = 0; x < width; ++x) {
    float &sample = amplitudeCurve[static_cast<unsigned>(x)];
    for (unsigned i = 0; i < portableBands.size(); ++i) {
      const auto &band = portableBands[i];
      if (band.enabled && band.on &&
          (band.forceCurve || std::fabs(band.gain) > 0.05f))
        sample = sample + bandCurves[i][static_cast<unsigned>(x)];
    }
    if (!bufferedDraw)
      pixelCurve[static_cast<unsigned>(x)] = gainToY(sample);
  }
  bufferValid = true;
  portableView->invalidate();
}
void EQControl::onIdle() {
  if (!observerControl)
    throw std::logic_error("EQControl control provider must be bound");
  observerControl->Core::Portable::Control::onIdle();
  // CCL POSIX getTime is nanoseconds, matching the native 1000000 divisor.
  // This is an intentional binding to the pinned clock API, not legacy Core.
  const std::int64_t now = Core::SystemClock::getTime() / 1000000;
  const auto elapsed = static_cast<std::uint64_t>(now) -
                       static_cast<std::uint64_t>(lastCurveTime);
  // Preserve ARM high-word signed comparison, including low-word borrow,
  // without invoking signed overflow in C++.
  const auto high = static_cast<std::uint32_t>(elapsed >> 32);
  if ((high != 0 && high < 0x80000000u) ||
      (high == 0 && static_cast<std::uint32_t>(elapsed) > 33u)) {
    rebuildCurves();
    lastCurveTime = now;
  }
}
} // namespace Presonus
