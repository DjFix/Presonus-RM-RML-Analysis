#include "presonus/dsp/Controller.hpp"
#include <bit>
#include <cstddef>
#include <cstring>
namespace Presonus::Dsp {
void Controller::setupProcess(const SetupProperty &property) {
  // Borrowed native property access, shared with the existing reverb port.
  // This does not establish an original SetupProperty declaration or layout.
  std::uint32_t rateBits;
  const auto *bytes = reinterpret_cast<const std::byte *>(&property);
  std::memcpy(&rateBits, bytes + 8, sizeof rateBits);
  if (std::bit_cast<float>(rateBits) !=
      std::bit_cast<float>(sourceState().processRateBits)) {
    sourceState().processDirty = 1;
    sourceState().processRateBits = rateBits;
  }
}
} // namespace Presonus::Dsp
