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
void ChannelComponent::postDoUpdates() { state().updates.fill(0); }

bool ChannelComponent::isLCRPanMode() const {
  auto &e = *state().environment;
  if (!e.panModeCache && e.globalParameters)
    e.panModeCache = e.globalParameters->getParameterByTag(45);
  const bool mode = e.panModeCache && e.panModeCache->getValue() > 0.f;
  const bool mono = state().monoAssign && state().monoAssign->getValue() > 0.f;
  const bool main = state().mainAssign && state().mainAssign->getValue() > 0.f;
  return mode && mono && main;
}

void ChannelComponent::removeLink() {
  const bool linked = services().isLinked(*this);
  float pan = 0.f;
  if (linked)
    pan = state().linkedPan->getValue() *
              ((state().linkSide & 1u) ? 0.5f : -0.5f) +
          0.5f;
  services().removeLink(*this);
  if (state().active && linked)
    state().pan->setValue(pan, false);
}

void ChannelComponent::levelUpdate() {
  const auto old = state().coefficients;
  const float level = state().level->getValue();
  state().gain =
      level < -144.f ? 6.309573308271865e-8f : std::pow(10.f, level * 0.05f);
  if (state().mute->getValue() != 0.f || state().level->getValue() <= -84.f)
    state().gain = 0.f;
  float pan = state().pan->getValue();
  if (services().isLinked(*this))
    pan = state().linkedPan->getValue() *
              ((state().linkSide & 1u) ? 0.5f : -0.5f) +
          0.5f;
  const float law = state().environment->panLaw;
  if (isLCRPanMode()) {
    state().coefficients.fill(0.f);
    if (pan < 0.5f) {
      const float center = pan + pan;
      state().coefficients[0] = state().gain * panCurve(1.f - center, law);
      state().coefficients[2] = state().gain * panCurve(center, law);
    } else {
      const float right = (pan - 0.5f) + (pan - 0.5f);
      state().coefficients[2] = state().gain * panCurve(1.f - right, law);
      state().coefficients[1] = state().gain * panCurve(right, law);
    }
  } else {
    state().coefficients[0] = state().gain * panCurve(1.f - pan, law);
    state().coefficients[1] = state().gain * panCurve(pan, law);
    state().coefficients[2] = state().gain;
  }
  if (!(old[0] == state().coefficients[0]) ||
      !(old[1] == state().coefficients[1]) ||
      !(old[2] == state().coefficients[2]))
    services().coefficientsChanged(*this, false);
}

void ChannelComponent::linkChannelName() {
  if (!state().name ||
      std::strcmp(state().name->getText(), state().name->getDefaultText()) == 0)
    return;
  auto *pair = services().linkablePair(*this);
  if (pair && pair->state().name)
    pair->state().name->fromString(state().name->getText(), false);
}
void ChannelComponent::doUpdates() {
  if (state().updates[0])
    levelUpdate();
  if (state().updates[1])
    soloCoeffUpdate();
}
void ChannelComponent::soloCoeffUpdate() {
  const auto old = state().soloCoefficients;
  auto &e = *state().environment;
  if (state().solo->getValue() == 0.f || e.soloBlockedA || e.soloBlockedB) {
    state().soloCoefficients.fill(0.f);
  } else {
    if (!state().soloModeCache)
      state().soloModeCache = e.soloParameters->getParameterByTag(12);
    if (state().soloModeCache && state().soloModeCache->getValue() > 0.f)
      state().soloCoefficients.fill(1.f);
    else
      state().soloCoefficients = {state().coefficients[0],
                                  state().coefficients[1]};
  }
  if (!(old[0] == state().soloCoefficients[0]) ||
      !(old[1] == state().soloCoefficients[1]))
    services().coefficientsChanged(*this, true);
}
void ChannelComponent::checkFaderLocateSync() {
  if (std::fabs(state().locatePosition->getValue() - state().lastLocate) >
      0.05f)
    services().faderLocateDirty(*this);
}
void ChannelComponent::resetEQDyn() {
  auto *globals = state().environment->globalParameters;
  auto *comp = globals->getParameterByTag(48);
  auto *gate = globals->getParameterByTag(47);
  auto *eq = globals->getParameterByTag(46);
  const bool resetComp = comp && comp->getValue() > 0.f;
  const bool resetGate = gate && gate->getValue() > 0.f;
  const bool resetEq = eq && eq->getValue() > 0.f;
  const auto reset = [&](bool enabled, const char *name) {
    if (enabled)
      if (auto *child = state().children->findChild(name))
        child->resetToDefaults(true, true, nullptr);
  };
  reset(resetComp, "comp");
  reset(resetGate, "gate");
  reset(resetEq, "eq");
}
bool ChannelComponent::handleFaderLocate(float value) const {
  if (!state().locateIndicator || !state().locatePosition || !state().level)
    return false;
  const float current = state().level->getNormalized();
  const float previous = state().locatePosition->getNormalized();
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
  state().locateIndicator->setValue(reached ? 0.5f : indicator / 14.f, false);
  return reached;
}
} // namespace Presonus::Mixer
