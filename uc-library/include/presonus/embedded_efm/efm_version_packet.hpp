#pragma once
#include <cstddef>
#include <cstdint>

namespace presonus::analysis::efm_fader_app {
// Independent partial command25 source port. Other commands are unsupported.
// Selector indexing deliberately follows original writes, including
// selectors>3.
bool applyVersionPacket(std::uint8_t *packet, std::size_t capacity,
                        std::uint8_t boardId);
} // namespace presonus::analysis::efm_fader_app
