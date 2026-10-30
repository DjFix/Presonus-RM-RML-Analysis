#pragma once
#include <cstddef>
#include <cstdint>

namespace presonus::analysis::efm_fader_packed_parameters {
// Independent portable byte-addressed RAM image. Offset zero corresponds to
// original RAM 0x20000000; this does not map or access actual device memory.
// Only commands20/22/28 and the original incoming-wrapper group0 are supported.
bool applyPackedParameterPacket(std::uint8_t *ram, std::size_t capacity);
} // namespace presonus::analysis::efm_fader_packed_parameters
