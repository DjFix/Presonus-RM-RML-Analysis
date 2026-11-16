#include "presonus/mixer/ParamLink.hpp"
#include "core/portable/corecomponent.h"
#include "core/public/corestringbuffer.h"
#include "core/system/coredebug.h"
#include <stdexcept>
namespace Presonus::Mixer {
ParamLink::ParamLink(Core::Portable::Parameter *parameter, const char *name,
                     bool flag)
    : ControlMapping(parameter, name), flag_(flag), target_(nullptr),
      observed_(parameter) {
  if (parameter)
    parameter->addObserver(this);
}
ParamLink::~ParamLink() {
  if (target_)
    target_->removeObserver(this);
  if (observed_)
    observed_->removeObserver(this);
}
void ParamLink::paramChanged(Core::Portable::Parameter *p, int reason) {
  if (reason == Core::Portable::Parameter::kDestroyed) {
    p->removeObserver(this);
    if (p == target_)
      target_ = nullptr;
    if (p == observed_)
      observed_ = nullptr;
    return;
  }
  if (reason != Core::Portable::Parameter::kChanged)
    return;
  auto *source = p == parameter() ? p : target_;
  auto *destination = p == parameter() ? target_ : parameter();
  if (!source || !destination)
    return;
  if (p->getType() == Core::Portable::ParamInfo::kString) {
    Core::CStringBuffer<64> text;
    source->toString(text.getBuffer(), 64);
    if (!text.isEmpty())
      destination->fromString(text.str(), true);
  } else
    destination->setValue(source->getValue(), true);
}
void ParamLink::connect(Presonus::MixerClientComponentBase *client) {
  if (client && (client != client_ || !clientRoot_))
    throw std::logic_error(
        "ParamLink client requires matching real root binding");
  if (target_)
    target_->removeObserver(this);
  target_ = client ? clientRoot_->lookupParameter(name()) : nullptr;
  if (target_) {
    if (parameter())
      target_->setValue(parameter()->getValue(), false);
    if (flag_)
      target_->addObserver(this);
  }
  if (parameter() &&
      parameter()->getType() == Core::Portable::ParamInfo::kString) {
    Core::CStringBuffer<64> text;
    parameter()->toString(text.getBuffer(), 64);
    if (!text.isEmpty()) {
      Core::DebugPrintf("ParamLink::connect sending param %s string=%s\n",
                        parameter()->getName(), text.str());
      parameter()->changed();
    }
  }
}
} // namespace Presonus::Mixer
