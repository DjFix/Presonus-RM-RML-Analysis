#include "presonus/dsp/GateController.hpp"

#include "presonus/dsp/ControllerProperties.hpp"
#include "presonus/mixer_dsp/GateParameterList.hpp"

#include <bit>
#include <cmath>
#include <limits>

namespace {
float sourceFloat(std::uint32_t bits) { return std::bit_cast<float>(bits); }

constexpr float minimumDecibels = -144.f;
constexpr float minimumAttack = 0x1.4f8b58p-16f;
constexpr float minimumRelease = 0x1.a36e2ep-14f;

float gainInDecibels(float gain) {
  return gain < sourceFloat(0x33877f3f) ? minimumDecibels
                                        : std::log10(gain) * 20.f;
}

float decibelsToGain(float decibels) {
  return decibels < minimumDecibels ? sourceFloat(0x33877f3f)
                                    : std::pow(10.f, decibels * .05f);
}

struct GateProperty : Core::Property {
  int channel;
  std::array<float, 5> coefficients;
  float range, inverseThreshold, attack, release, attackSmoothing,
      releaseSmoothing;
  int releaseSamples, enabled, expander, keyListen;

  explicit GateProperty(int channel,
                        const presonus::dsp::GateControllerSourceState &gate)
      : Property(0x67617465, sizeof(GateProperty)), channel(channel),
        coefficients(gate.coefficients), range(gate.range),
        inverseThreshold(gate.inverseThreshold), attack(gate.attack),
        release(gate.release), attackSmoothing(gate.attackSmoothing),
        releaseSmoothing(gate.releaseSmoothing),
        releaseSamples(gate.releaseSamples), enabled(gate.enabled),
        expander(gate.expander), keyListen(gate.keyListen) {}
};

static_assert(sizeof(GateProperty) == 72);
} // namespace

namespace Presonus::Dsp {
GateController::GateController(int id)
    : Controller(id, &presonus::dsp::sourceList(*GateParamList::instance())) {
  setDefaultValues();
}

GateController::~GateController() = default;

float GateController::getValue(int tag) const {
  switch (tag) {
  case 0:
    return gate_.enabled != 0;
  case 1:
    return gate_.keyListen != 0;
  case 2:
  case 8:
    return gate_.expander != 0;
  case 3:
    return gate_.filterFrequency;
  case 4:
    return -gainInDecibels(gate_.inverseThreshold);
  case 5:
    return gainInDecibels(gate_.range);
  case 6:
    return gate_.attack;
  case 7:
    return gate_.release;
  case 9:
    return gainInDecibels(gate_.reduction);
  default:
    return 0.f;
  }
}

float GateController::setValue(int tag, float value) {
  // The ARM body leaves varying incidental values in r0. The portable
  // interface returns the submitted value, as the EQ control port does.
  if (tag >= getNumParameters())
    return value;
  auto &base = sourceState();
  base.processDirty =
      base.processDirty || gate_.enabled || tag == 0 || tag == 1 || tag == 3;
  switch (tag) {
  case 0:
    gate_.enabled = value != 0.f;
    break;
  case 1:
    gate_.keyListen = value != 0.f;
    break;
  case 2:
    gate_.expander = value != 0.f;
    base.word20 |= 1;
    break;
  case 3:
    gate_.filterFrequency = value < 40.f ? 40.f : value;
    gate_.filterMode = value > sourceFloat(0x42200106) ? 7 : -1;
    break;
  case 4:
    gate_.inverseThreshold = decibelsToGain(
        sourceFloat(std::bit_cast<std::uint32_t>(value) ^ 0x80000000u));
    break;
  case 5:
    gate_.range = decibelsToGain(value);
    break;
  case 6:
    gate_.attack = value;
    break;
  case 7:
    gate_.release = value;
    break;
  }
  return value;
}

void GateController::setupProcess(const SetupProperty &property) {
  auto &base = sourceState();
  if (property.rate != sourceFloat(base.processRateBits)) {
    base.processRateBits = std::bit_cast<std::uint32_t>(property.rate);
    filter_.setup(property.reserved, static_cast<double>(property.rate));
    filter_.flush();
    base.processDirty = 1;
  }
  Controller::setupProcess(property);
}

void GateController::doUpdates() {
  filter_.setParams(gate_.filterMode, gate_.filterFrequency, gate_.filterQ,
                    gate_.filterGain);
  const auto &filter = filter_.portableState();
  for (std::size_t i = 0; i < gate_.coefficients.size(); ++i)
    gate_.coefficients[i] = static_cast<float>(filter.coefficients[i]);

  if (!(gate_.attack > minimumAttack))
    gate_.attack = minimumAttack;
  if (!(gate_.release > minimumRelease))
    gate_.release = minimumRelease;
  const float rate = sourceFloat(sourceState().processRateBits);
  const float reciprocal = 1.f / (rate * .25f);
  const float exponent = sourceFloat(0xc0c90fdb);
  const float release = gate_.release * (gate_.expander ? 1.f : .5f);
  gate_.attackSmoothing =
      std::exp(((1.f / gate_.attack) * exponent) * reciprocal);
  gate_.releaseSmoothing = std::exp(((1.f / release) * exponent) * reciprocal);
  const float samples = (release * rate) * .5f;
  if (samples >= static_cast<float>(std::numeric_limits<int>::max()))
    gate_.releaseSamples = std::numeric_limits<int>::max();
  else
    gate_.releaseSamples = samples >= 1.f ? static_cast<int>(samples) : 1;

  GateProperty property(std::bit_cast<int>(sourceState().word04), gate_);
  sendProperty(property);
}
} // namespace Presonus::Dsp
