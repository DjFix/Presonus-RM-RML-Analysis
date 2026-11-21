#pragma once

#include "core/public/coreproperty.h"
#include "presonus/DspComponent.hpp"

namespace Presonus::Dsp {
class Controller;
}

namespace Presonus::Mixer {
// Portable source port of the observed lifecycle. The caller transfers the
// release obligations for both arguments. The controller must be non-null and
// must borrow the target passed to setTarget. The target must be non-null.
class AudioComponent : public DspComponent {
public:
  AudioComponent(const char *, Dsp::Controller *, Core::IPropertyHandler *,
                 int);
  ~AudioComponent() override;

private:
  Core::IPropertyHandler *propertyHandler_;
};
} // namespace Presonus::Mixer
