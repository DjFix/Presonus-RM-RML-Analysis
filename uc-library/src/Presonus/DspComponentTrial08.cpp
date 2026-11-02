#include "presonus/trial08/DspComponent.hpp"
#include <algorithm>
#include <stdexcept>
namespace Presonus {
DspComponent::DspComponent(const char *name, Dsp::IController *controller)
    : name_(name), controller_(controller) {}
dspcomponent_port::Boundary &DspComponent::boundary() const {
  if (!boundary_)
    throw std::logic_error("DspComponent requires an application boundary");
  return *boundary_;
}
Dsp::IController *DspComponent::getController() { return controller_; }
void DspComponent::construct() { syncValues(true); }
bool DspComponent::isDspParameter(Core::Portable::Parameter *p) const {
  return static_cast<int>(p->getType()) <= 3;
}
void *DspComponent::castTo(int id) {
  switch (id) {
  case 1148416067:
  case 1282304865:
  case 1400259439:
  case 1131375984:
    return this;
  default:
    return nullptr;
  }
}
int DspComponent::load(const Core::Portable::InputStorage &storage) {
  int result = boundary().load(storage);
  if (controller_) {
    unsigned f = boundary().flags(*controller_);
    if (f & 2)
      syncValues(false);
    else if (f & 1)
      syncReadouts();
  }
  return result;
}
void DspComponent::syncReadouts() {
  for (unsigned i = 0; i < count_; ++i) {
    auto *p = readouts_[i];
    p->setValue(boundary().value(*controller_, p->getTag()), false);
  }
}
void DspComponent::onIdle() {
  if (controller_) {
    unsigned f = boundary().flags(*controller_);
    boundary().acknowledge(*controller_);
    if (f & 2)
      syncValues(false);
    else if (f & 1)
      syncReadouts();
  }
  boundary().idle();
}
void DspComponent::paramChanged(Core::Portable::Parameter *p, int reason) {
  if (reason == 2 && isDspParameter(p) && controller_)
    boundary().set(*controller_, p->getTag(), p->getValue());
  if (forwarding_)
    boundary().changed(p, reason);
}
void DspComponent::syncValues(bool build) {
  if (build)
    count_ = 0;
  if (!controller_)
    return;
  int n = std::min(boundary().count(*controller_),
                   static_cast<int>(parameters_.size()));
  int ordinal = 0;
  for (int i = 0; i < n; ++i) {
    auto *p = parameters_[i];
    if (!isDspParameter(p))
      continue;
    p->setValue(boundary().value(*controller_, p->getTag()), false);
    int accepted = ordinal++;
    if (build && boundary().readout(*controller_, accepted) && count_ < 10)
      readouts_[count_++] = p;
  }
}
} // namespace Presonus
