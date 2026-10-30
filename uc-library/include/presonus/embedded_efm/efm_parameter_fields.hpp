#pragma once
#include <cstddef>
#include <cstdint>

namespace presonus::analysis::efm_fader_parameters {
// Independent analysis interfaces; no original source declarations/ABI claimed.
enum class Transfer {
  ReadByte,
  WriteByte,
  ReadWordLowByte,
  WriteZeroExtendedWord
};
bool transferStrided(Transfer operation, std::uint8_t *packet,
                     std::size_t packetCapacity, std::uint8_t *state,
                     std::size_t stateCapacity, std::uint32_t stateStride,
                     std::uint32_t packetStride, std::uint8_t first,
                     std::uint8_t last);
// Partial dispatcher: only commands21/23/29/2a and their high-bit forms.
bool applyParameterPacket(std::uint8_t *packet, std::size_t packetCapacity,
                          std::uint8_t *context, std::size_t contextCapacity,
                          std::uint8_t boardId);
} // namespace presonus::analysis::efm_fader_parameters
