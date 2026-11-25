#include "presonus/dsp/CompController.hpp"
#include "presonus/mixer_dsp/CompressorParameterList.hpp"
#include "presonus/mixer_dsp/CompressorSourceProviders.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <stdexcept>

namespace {

constexpr float fromWord(std::uint32_t word) {
  return std::bit_cast<float>(word);
}

constexpr float log2PerDecibel = fromWord(0x3eaa1615);
constexpr float amplitudeFloor = fromWord(0x33877f3f);

const Presonus::Dsp::ParamDescriptorList *compressorParameters() {
  if (!presonus::dsp::compressorSourcePortProvidersReady())
    throw std::logic_error("Compressor controller requires provider bootstrap");
  return &presonus::dsp::sourceList(
      *Presonus::Dsp::CompressorParamList::instance());
}

float amplitudeToDecibels(float amplitude) {
  return amplitude < amplitudeFloor ? -144.f : std::log10(amplitude) * 20.f;
}

float singlePole(float frequency, float rate) {
  return std::exp((frequency * fromWord(0xc0c90fdb)) * (1.f / rate));
}

struct CompressorProperty : Core::Property {
  explicit CompressorProperty(std::uint32_t channelWord)
      : Property(FOUR_CHAR_ID('c', 'o', 'm', 'p'), sizeof(CompressorProperty)),
        channel(channelWord) {}

  std::uint32_t channel;
  std::array<float, 72> values;
  std::uint32_t enabled;
};

static_assert(sizeof(CompressorProperty) == 304);

} // namespace

namespace Presonus::Dsp {

CompController::CompController(int id)
    : Controller(id, compressorParameters()),
      tableThreshold_(fromWord(0x3b449ba6)), lowerKnee_(tableThreshold_) {
  sourceState().word08 = 0;
  setDefaultValues();
}

CompController::~CompController() = default;

float CompController::getValue(int tag) const {
  switch (tag) {
  case 0:
    return enabled_;
  case 1:
    return softKnee_;
  case 2:
    return automatic_;
  case 3:
    return thresholdLog_ / log2PerDecibel;
  case 4:
    return inverseRatio_ > 0.f ? 1.f / inverseRatio_ : 20.f;
  case 5:
    return attack_;
  case 6:
    return release_;
  case 7:
    return amplitudeToDecibels(gain_);
  case 8:
    return amplitudeToDecibels(reduction_);
  case 9:
    return softKnee_ ? 3.f : 0.f;
  default:
    return 0.f;
  }
}

float CompController::setValue(int tag, float value) {
  auto &state = sourceState();
  state.processDirty = state.processDirty || tag == 0 || enabled_;
  switch (tag) {
  case 0:
    enabled_ = value != 0.f;
    break;
  case 1:
    state.word20 |= 1;
    softKnee_ = value != 0.f;
    break;
  case 2:
    automatic_ = value != 0.f;
    break;
  case 3:
    thresholdLog_ = value * log2PerDecibel;
    tableThreshold_ = std::pow(2.f, thresholdLog_);
    break;
  case 4:
    inverseRatio_ = value > 0.f ? 1.f / value : 1.f;
    break;
  case 5:
    attack_ = boundValue(tag, value);
    break;
  case 6:
    release_ = boundValue(tag, value);
    break;
  case 7:
    gain_ = value < -144.f ? amplitudeFloor : std::pow(10.f, value * .05f);
    break;
  }
  return value;
}

void CompController::doUpdates() {
  const auto &state = sourceState();
  const float rate = std::bit_cast<float>(state.processRateBits);
  const float workingRate = rate * .25f;
  envelopeCoefficient_ = singlePole(150.f, workingRate);
  releaseCoefficient_ = 1.f / (((automatic_ ? .01f : attack_) * rate) * .25f);
  attackCoefficient_ = singlePole(
      automatic_ ? fromWord(0x40d55555) : 1.f / release_, workingRate);
  const float threshold = thresholdLog_ < 0.f ? thresholdLog_ : 0.f;
  const float slope = (1.f - inverseRatio_) * .5f;
  const float kneeWidth = softKnee_ ? 3.f : 0.f;
  const float curvature = (slope * -.25f) / kneeWidth;
  detectorCoefficient_ = singlePole(500.f, workingRate);

  const float kneeBase =
      threshold > (softKnee_ ? -3.f : -0.f) ? -threshold : kneeWidth;
  lowerKnee_ = std::pow(2.f, threshold - kneeBase);
  tableThreshold_ = lowerKnee_;
  const float upperKnee = std::pow(2.f, threshold + kneeBase);
  const float step = (1.f - lowerKnee_) / 3969.f;
  inverseStep_ = step != 0.f ? 1.f / step : 0.f;
  for (unsigned i = 0; i < table_.size(); ++i) {
    const float input = lowerKnee_ + static_cast<float>(i * i) * step;
    const float inputLog = std::log(input) * fromWord(0x3fb8aa3b);
    if (upperKnee > input) {
      const float distance = kneeBase + (inputLog - threshold);
      table_[i] = std::pow(2.f, (curvature * distance) * distance);
    } else {
      table_[i] = std::pow(2.f, (threshold - inputLog) * slope);
    }
  }

  CompressorProperty property(state.word04);
  std::copy(table_.begin(), table_.end(), property.values.begin());
  property.values[64] = tableThreshold_;
  property.values[65] = gain_;
  property.values[66] = inverseStep_;
  property.values[67] = releaseCoefficient_;
  property.values[68] = attackCoefficient_;
  property.values[69] = envelopeCoefficient_;
  property.values[70] = detectorCoefficient_;
  property.values[71] = lowerKnee_;
  property.enabled = enabled_;
  sendProperty(property);
}

} // namespace Presonus::Dsp
