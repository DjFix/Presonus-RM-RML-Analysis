#include "presonus/surface/SLMappingState.hpp"
#include <cstdint>
#include <cstring>
#include <stdexcept>
namespace Presonus::Surface {
int EQPageComponent::getEqEncoderMode() const {
  auto *parameter = encoderParameters_.byTag(1000);
  if (!parameter)
    throw std::logic_error("missing EQ encoder parameter");
  // Defined source-port float-to-int domain is finite and int-representable.
  return static_cast<int>(parameter->getValue());
}
} // namespace Presonus::Surface
