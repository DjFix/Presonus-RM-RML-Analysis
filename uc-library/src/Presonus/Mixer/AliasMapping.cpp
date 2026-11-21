#include "presonus/mixer/AliasMapping.hpp"
#include "core/portable/corecomponent.h"
#include <stdexcept>
namespace Presonus::Mixer {
AliasMapping::AliasMapping(Core::Portable::AliasParam *alias,
                           Core::Portable::Parameter *parameter,
                           const char *name)
    : ControlMapping(parameter, name), alias_(alias) {}

void AliasMapping::bindMixerRoot(MixerClientComponentBase &mixer,
                                 Core::Portable::Component &root) {
  mixer_ = &mixer;
  root_ = &root;
}

void AliasMapping::connect(MixerClientComponentBase *mixer) {
  Core::Portable::Parameter *target = nullptr;
  if (mixer) {
    if (mixer != mixer_)
      throw std::logic_error("AliasMapping requires the mixer's CCL root");
    target = root_->lookupParameter(name());
  }
  const bool enabled = alias_->isEnabled();
  alias_->setOriginal(target ? target : parameter());
  alias_->enable(enabled);
}
} // namespace Presonus::Mixer
