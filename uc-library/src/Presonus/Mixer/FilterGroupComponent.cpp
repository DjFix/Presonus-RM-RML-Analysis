#include "presonus/mixer/FilterGroupComponent.hpp"
#include "core/portable/coreparams.h"

namespace Presonus::Mixer {
bool FilterGroupComponent::isConfigured() {
  auto *parameter = getParameterByTag(600);
  if (!parameter)
    return false;
  // CCL's live class query replaces the original __dynamic_cast boundary.
  auto *text = Core::Portable::StringParam::cast(parameter);
  // Intentional source mapping of the native StringParam+0x2c byte predicate
  // to the pinned provider's text API; no original ARM offset/layout claim.
  return text && !text->getText().isEmpty();
}
} // namespace Presonus::Mixer
