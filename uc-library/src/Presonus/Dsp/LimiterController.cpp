#include "presonus/dsp/LimiterController.hpp"
#include "presonus/dsp/ControllerProperties.hpp"
#include "presonus/mixer_dsp/Eq8LimiterParameterLists.hpp"
#include <bit>
#include <cmath>

namespace {
constexpr float minimumAmplitude = std::bit_cast<float>(0x33877f3fu);

float singlePole(float frequency, float sampleRate) {
  constexpr float negativeTwoPi = std::bit_cast<float>(0xc0c90fdbu);
  return std::exp((frequency * negativeTwoPi) * (1.f / sampleRate));
}
} // namespace

namespace Presonus::Dsp {
LimiterController::LimiterController(int id)
    : Controller(id,
                 &presonus::dsp::sourceList(*LimiterParamList::instance())) {
  limiter_.smoothing = singlePole(2.5f, 48000.f);
  setDefaultValues();
}

LimiterController::~LimiterController() = default;

float LimiterController::getValue(int tag) const {
  switch (tag) {
  case 0:
    return limiter_.enabled != 0 ? 1.f : 0.f;
  case 1:
    return limiter_.thresholdAmplitude < minimumAmplitude
               ? 144.f
               : -(20.f * std::log10(limiter_.thresholdAmplitude));
  case 2:
    return limiter_.reductionAmplitude < minimumAmplitude
               ? -144.f
               : 20.f * std::log10(limiter_.reductionAmplitude);
  default:
    return 0.f;
  }
}

float LimiterController::setValue(int tag, float value) {
  auto &dirty = sourceState().processDirty;
  dirty = dirty || tag == 0 || limiter_.enabled;
  if (tag == 0) {
    limiter_.enabled = value != 0.f;
  } else if (tag == 1) {
    const float level = -value;
    limiter_.thresholdAmplitude =
        level < -144.f ? minimumAmplitude : std::pow(10.f, level * 0.05f);
  }
  // The portable Controller setter requires a float. The native register
  // contents vary by branch and do not establish a float return declaration.
  return value;
}

void LimiterController::doUpdates() {
  limiter_.smoothing =
      singlePole(2.5f, std::bit_cast<float>(sourceState().processRateBits));

  ChannelProperty property;
  property.type = 0x6c696d20;
  // The shared host property has a channel followed by storage for EQ data.
  // For this type only its first three data words are part of the message.
  property.size = 24;
  property.entries.front().band = std::bit_cast<int>(limiter_.enabled);
  property.entries.front().coefficients[0] = limiter_.thresholdAmplitude;
  property.entries.front().coefficients[1] = limiter_.smoothing;
  sendProperty(property, true);
}
} // namespace Presonus::Dsp
