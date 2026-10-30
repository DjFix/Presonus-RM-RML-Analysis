#pragma once
#include <cstddef>
#include <cstdint>

namespace presonus::analysis::efm_fader_control_dispatch {
// Independent control boundary, not an original firmware interface or provider.
enum class ControlEntry : std::uint32_t {
  Entry16bc = 0x16bc,
  Entry1fa8 = 0x1fa8
};
class ControlBoundary {
public:
  virtual ~ControlBoundary() = default;
  // First entry's explicitArgument is normalized to zero: no original second
  // argument declaration is asserted. Entry1fa8 has observed R1 value four.
  virtual void call(ControlEntry entry, std::uint32_t contextRamOffset,
                    std::uint32_t explicitArgument) = 0;
};
// Full observed RAM behavior of original entry0x24d8, with portable bounds.
bool initialiseIndexedState(std::uint8_t *ram, std::size_t capacity);
// Defaults and commands11/24/26 only. Command11 remains partial at the two
// mandatory control boundaries; no peripheral implementation is provided.
bool dispatchControlPacket(std::uint8_t *ram, std::size_t capacity,
                           ControlBoundary &boundary);
} // namespace presonus::analysis::efm_fader_control_dispatch
