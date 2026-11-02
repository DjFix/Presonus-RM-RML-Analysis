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
