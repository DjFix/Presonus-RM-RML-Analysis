#include "presonus/mixer/GEQLinkHandler.hpp"

namespace Presonus::Mixer {
using Core::Portable::Parameter;

GEQLinkHandler::GEQLinkHandler(Parameter *destination, Parameter *source)
    : Component(""), destination_(destination), source_(source) {
  if (source_)
    source_->addObserver(this);
}

GEQLinkHandler::~GEQLinkHandler() = default;

void GEQLinkHandler::paramChanged(Parameter *parameter, int message) {
  if (message == Parameter::kDestroyed)
    parameter->removeObserver(this);
  else if (message == Parameter::kChanged && destination_)
    destination_->setValue(parameter->getValue(), true);
}
} // namespace Presonus::Mixer
