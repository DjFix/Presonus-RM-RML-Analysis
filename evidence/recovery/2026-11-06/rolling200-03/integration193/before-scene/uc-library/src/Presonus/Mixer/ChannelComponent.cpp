#include "presonus/mixer/ChannelComponent.hpp"
#include <cmath>
#include <cstring>

namespace Presonus::Mixer {
namespace {
float panCurve(float value, float law) {
  // Keep the native sequence of separately rounded float operations.
  const float squarePart = (value * law) * value;
  const float linearPart = value * (1.f - law);
  return squarePart + linearPart;
}
} // namespace
void ChannelComponent::postDoUpdates() { state_.updates.fill(0); }

bool ChannelComponent::isLCRPanMode() const {
  auto &e = *state_.environment;
  if (!e.panModeCache && e.globalParameters)
    e.panModeCache = e.globalParameters->getParameterByTag(45);
  const bool mode = e.panModeCache && e.panModeCache->getValue() > 0.f;
  const bool mono = state_.monoAssign && state_.monoAssign->getValue() > 0.f;
  const bool main = state_.mainAssign && state_.mainAssign->getValue() > 0.f;
  return mode && mono && main;
}

void ChannelComponent::removeLink() {
  const bool linked = services_.isLinked(*this);
  float pan = 0.f;
  if (linked)
    pan =
        state_.linkedPan->getValue() * ((state_.linkSide & 1u) ? 0.5f : -0.5f) +
        0.5f;
  services_.removeLink(*this);
  if (state_.active && linked)
    state_.pan->setValue(pan, false);
}

void ChannelComponent::levelUpdate() {
  const auto old = state_.coefficients;
  const float level = state_.level->getValue();
  state_.gain =
      level < -144.f ? 6.309573308271865e-8f : std::pow(10.f, level * 0.05f);
  if (state_.mute->getValue() != 0.f || state_.level->getValue() <= -84.f)
    state_.gain = 0.f;
  float pan = state_.pan->getValue();
  if (services_.isLinked(*this))
    pan =
        state_.linkedPan->getValue() * ((state_.linkSide & 1u) ? 0.5f : -0.5f) +
        0.5f;
  const float law = state_.environment->panLaw;
  if (isLCRPanMode()) {
    state_.coefficients.fill(0.f);
    if (pan < 0.5f) {
      const float center = pan + pan;
      state_.coefficients[0] = state_.gain * panCurve(1.f - center, law);
      state_.coefficients[2] = state_.gain * panCurve(center, law);
    } else {
      const float right = (pan - 0.5f) + (pan - 0.5f);
      state_.coefficients[2] = state_.gain * panCurve(1.f - right, law);
      state_.coefficients[1] = state_.gain * panCurve(right, law);
    }
  } else {
    state_.coefficients[0] = state_.gain * panCurve(1.f - pan, law);
    state_.coefficients[1] = state_.gain * panCurve(pan, law);
    state_.coefficients[2] = state_.gain;
  }
  if (!(old[0] == state_.coefficients[0]) ||
      !(old[1] == state_.coefficients[1]) ||
      !(old[2] == state_.coefficients[2]))
    services_.coefficientsChanged(*this, false);
}

void ChannelComponent::linkChannelName() {
  if (!state_.name ||
      std::strcmp(state_.name->getText(), state_.name->getDefaultText()) == 0)
    return;
  auto *pair = services_.linkablePair(*this);
  if (pair && pair->state_.name)
    pair->state_.name->fromString(state_.name->getText(), false);
}
void ChannelComponent::doUpdates() {
  if (state_.updates[0])
    levelUpdate();
  if (state_.updates[1])
    soloCoeffUpdate();
}
void ChannelComponent::soloCoeffUpdate() {
  const auto old = state_.soloCoefficients;
  auto &e = *state_.environment;
  if (state_.solo->getValue() == 0.f || e.soloBlockedA || e.soloBlockedB) {
    state_.soloCoefficients.fill(0.f);
  } else {
    if (!state_.soloModeCache)
      state_.soloModeCache = e.soloParameters->getParameterByTag(12);
    if (state_.soloModeCache && state_.soloModeCache->getValue() > 0.f)
      state_.soloCoefficients.fill(1.f);
    else
      state_.soloCoefficients = {state_.coefficients[0],
                                 state_.coefficients[1]};
  }
  if (!(old[0] == state_.soloCoefficients[0]) ||
      !(old[1] == state_.soloCoefficients[1]))
    services_.coefficientsChanged(*this, true);
}
void ChannelComponent::checkFaderLocateSync() {
  if (std::fabs(state_.locatePosition->getValue() - state_.lastLocate) > 0.05f)
    services_.faderLocateDirty(*this);
}
void ChannelComponent::resetEQDyn() {
  auto *globals = state_.environment->globalParameters;
  auto *comp = globals->getParameterByTag(48);
  auto *gate = globals->getParameterByTag(47);
  auto *eq = globals->getParameterByTag(46);
  const bool resetComp = comp && comp->getValue() > 0.f;
  const bool resetGate = gate && gate->getValue() > 0.f;
  const bool resetEq = eq && eq->getValue() > 0.f;
  const auto reset = [&](bool enabled, const char *name) {
    if (enabled)
      if (auto *child = state_.children->findChild(name))
        child->resetToDefaults(true, true, nullptr);
  };
  reset(resetComp, "comp");
  reset(resetGate, "gate");
  reset(resetEq, "eq");
}
bool ChannelComponent::handleFaderLocate(float value) const {
  if (!state_.locateIndicator || !state_.locatePosition || !state_.level)
    return false;
  const float current = state_.level->getNormalized();
  const float previous = state_.locatePosition->getNormalized();
  bool reached = (current < previous && current >= value) ||
                 (current > previous && current <= value);
  const float difference = value * 255.f + current * -255.f;
  const bool negative = difference < 0.f;
  const float distance = negative ? -difference : difference;
  const float direction = negative ? -1.f : 1.f;
  if (distance < 1.f)
    reached = true;
  float indicator = 7.f;
  for (float threshold : {1.f, 2.f, 3.f, 7.f, 19.f, 50.f, 100.f})
    if (distance >= threshold)
      indicator += direction;
  state_.locateIndicator->setValue(reached ? 0.5f : indicator / 14.f, false);
  return reached;
}
} // namespace Presonus::Mixer
