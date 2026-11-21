#include "presonus/mixer/GEQComponent.hpp"
#include "core/portable/coreparams.h"
#include "core/public/coreproperty.h"
#include <utility>
namespace Presonus::Mixer {
GEQComponent::GEQComponent(AdoptLifecycle,
                           std::unique_ptr<Presonus::DspComponent> dsp,
                           Core::IPropertyHandler *handler, const char *name)
    : Core::Portable::Component(name), dsp_(std::move(dsp)), handler_(handler) {
}

GEQComponent::~GEQComponent() {
  if (handler_)
    handler_->release();
}

void GEQComponent::flatten() {
  for (int tag = 0; tag < 31; ++tag)
    if (auto *p = getParameterByTag(tag))
      p->resetValue(true);
}
} // namespace Presonus::Mixer
