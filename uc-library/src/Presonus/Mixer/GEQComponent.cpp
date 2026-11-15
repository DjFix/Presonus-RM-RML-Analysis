#include "presonus/mixer/GEQComponent.hpp"
#include "core/portable/coreparams.h"
namespace Presonus::Mixer {
void GEQComponent::flatten() {
  for (int tag = 0; tag < 31; ++tag)
    if (auto *p = getParameterByTag(tag))
      p->resetValue(true);
}
} // namespace Presonus::Mixer
