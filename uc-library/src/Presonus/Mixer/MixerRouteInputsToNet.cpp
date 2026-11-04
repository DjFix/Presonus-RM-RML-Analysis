#include "core/portable/coreparams.h"
#include "core/public/corestringbuffer.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include <cstring>
#include <stdexcept>

namespace Presonus::Mixer {
void MixerComponentBase::routeInputsToNet() {
  // Preserve signed ARM comparisons without widening the original bit domain.
  const auto count = [this] {
    std::int32_t value;
    static_assert(sizeof(value) == sizeof(hardwareMicLineInputs));
    std::memcpy(&value, &hardwareMicLineInputs, sizeof(value));
    return value;
  };
  for (std::int32_t index = 0; index < count(); ++index) {
    if (!routeInputParameters)
      throw std::logic_error("routing requires a borrowed CCL component tree");
    Core::CString32 name("");
    name.appendFormat("ch%d", index + 1);
    auto *line = routeInputParameters->findChild("line");
    if (!line)
      continue;
    auto *channel = line->findChild(name.str());
    if (!channel)
      continue;
    auto *parameter = channel->getParameterByTag(0x130);
    // The original has no null guard. Missing parameters are outside the native
    // valid-object domain; the source port reports a binding error explicitly.
    if (!parameter)
      throw std::logic_error("routing channel requires parameter tag 0x130");
    parameter->changed();
  }
}
} // namespace Presonus::Mixer
