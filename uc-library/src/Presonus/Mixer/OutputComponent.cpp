#include "presonus/mixer/OutputComponent.hpp"
#include <cstring>
#include <stdexcept>
namespace Presonus::Mixer {
void OutputComponent::soloUpdate(Presonus::Dsp::MultiParamProperty &opaque) {
  auto &property = bindings_.resolveProperty(opaque);
  for (int i = 0; i < 2; ++i) {
    const float value = bindings_.channel.soloCoefficients[i];
    if (bindings_.cachedSolo[i] == value)
      continue;
    // Native cache updates precede capacity checks, including a full property.
    bindings_.cachedSolo[i] = value;
    if (property.count > 59)
      continue;
    if (property.count < 0)
      throw std::out_of_range("negative property count");
    std::uint32_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    property.entries[property.count++] = {i + 4, bits};
  }
}
} // namespace Presonus::Mixer

#include "presonus/mixer/OutputComponent.hpp"
#include <stdexcept>

namespace Presonus::Mixer {
void OutputComponent::paramChanged(Core::Portable::Parameter *parameter,
                                   int message) {
  if (!bindings_.channelParamChanged)
    throw std::logic_error("OutputComponent requires channelParamChanged");
  bindings_.channelParamChanged(parameter, message);
  // Native code reads the tag after the Channel callback, even for messages
  // other than kChanged. Parameter must therefore remain alive throughout.
  const int tag = parameter->getTag();
  if (message != Core::Portable::Parameter::kChanged)
    return;
  if (tag == 14) {
    bindings_.outputCoeffChanged = 1;
    bindings_.updatePending = true;
  } else if (tag == 400) {
    bindings_.updatePending = true;
  }
}

void OutputComponent::setSectionCoeffChanged(int section) {
  if (!bindings_.channelSectionCoeffChanged)
    throw std::logic_error(
        "OutputComponent requires channelSectionCoeffChanged");
  bindings_.channelSectionCoeffChanged(section);
  if (section == 1)
    bindings_.sectionOneCoeffChanged = 1;
}
} // namespace Presonus::Mixer
