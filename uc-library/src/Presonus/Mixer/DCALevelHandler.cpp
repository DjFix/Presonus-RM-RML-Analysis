#include "presonus/mixer/DCALevelHandler.hpp"
#include "presonus/mixer/FilterGroupComponent.hpp"

#include <cmath>

namespace Presonus::Mixer {
namespace {
constexpr float dbFloor = -144.f;
constexpr float amplitudeFloor = 6.309573308271865e-08f;
} // namespace

using Core::Portable::Parameter;

DCALevelHandler::DCALevelHandler(Parameter *level, Parameter *trim, int tag)
    : Component(""), level_(level), trim_(trim), masters_(0, 5), tag_(tag) {
  level_->addObserver(this);
  level_->changed();
}

DCALevelHandler::~DCALevelHandler() { level_->removeObserver(this); }

void DCALevelHandler::addDCAMaster(FilterGroupComponent *group) {
  auto *parameter = group->getParameterByTag(tag_);
  if (!parameter || masters_.contains(parameter))
    return;
  if (masters_.count() == masters_.getCapacity() &&
      !masters_.resize(masters_.count() + 1))
    return;
  masters_.add(parameter);
}

void DCALevelHandler::removeDCAMaster(FilterGroupComponent *group) {
  if (auto *parameter = group->getParameterByTag(tag_))
    masters_.remove(parameter);
}

float DCALevelHandler::getDBValue(Parameter *parameter) {
  const float minimum = parameter->getMin();
  const float value = parameter->getValue();
  if (minimum != 0.f)
    return value;
  return value < amplitudeFloor ? dbFloor : 20.f * std::log10(value);
}

void DCALevelHandler::setDBValue(Parameter *parameter, float db) {
  if (parameter->getMin() == 0.f)
    db = db < dbFloor ? amplitudeFloor : std::pow(10.f, db * 0.05f);
  parameter->setValue(db, true);
}

void DCALevelHandler::onDCAChange(bool respectLinkableFlag) {
  if (respectLinkableFlag && level_->isLinkable())
    return;
  busy_ = true;
  float db = trim_->getValue();
  const int count = masters_.count();
  for (int i = 0; i < count; ++i)
    db += masters_[i]->getValue();
  setDBValue(level_, db);
  busy_ = false;
}

void DCALevelHandler::onLevelChange() {
  if (busy_)
    return;
  float db = getDBValue(level_);
  const int count = masters_.count();
  for (int i = 0; i < count; ++i)
    db -= masters_[i]->getValue();
  trim_->setValue(db, false);
}

void DCALevelHandler::paramChanged(Parameter *parameter, int message) {
  if (message == Parameter::kChanged && parameter == level_)
    onLevelChange();
}

} // namespace Presonus::Mixer
