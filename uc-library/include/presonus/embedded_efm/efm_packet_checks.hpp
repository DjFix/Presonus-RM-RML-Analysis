#pragma once
#include <cstddef>
#include <cstdint>

namespace presonus::analysis::efm_fader_app {
// Independent checked source port, not an original firmware declaration/ABI.
// Caller capacity guards are portable adaptations; rejected inputs do not
// mutate.
bool appendPacketChecks(std::uint8_t *packet, std::size_t capacity);
bool validatePacketChecks(const std::uint8_t *packet, std::size_t capacity,
                          unsigned &originalResult);
} // namespace presonus::analysis::efm_fader_app
