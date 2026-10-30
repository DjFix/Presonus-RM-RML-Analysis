#include "core/system/coredebug.h"
#include "presonus/application/LPCProgrammerGeometry.hpp"
namespace Presonus {
int LPCProgrammer::initAddresses() {
  auto &state = imageState;
  const std::uint32_t last = getLastSector(state.raw18);
  state.raw34 = state.raw30 * 4096u;
  state.raw48 = last;
  state.raw38 = last;
  state.raw40 = state.raw30;
  bool uniform = false;
  switch (state.raw18) {
  case 620761368u:
    state.raw38 = 7;
    uniform = true;
    break;
  case 620761377u:
  case 436340005u:
    state.raw38 = 15;
    uniform = true;
    break;
  case 620828450u:
  case 637606178u:
    state.raw38 = 17;
    break;
  case 620828451u:
  case 637613875u:
  case 637615923u:
    state.raw38 = 21;
    break;
  case 620838711u:
  case 637610039u:
  case 637615927u:
  case 638664503u:
    state.raw38 = 29;
    break;
  default:
    Core::DebugPrintf("[e] Unknown part id (%08x)\n", state.raw18);
    state.raw38 = 0;
    state.raw48 = 0;
    state.raw4c = 0;
    return 0;
  }
  if (uniform || state.raw08 < 65536u) {
    state.raw48 = ((state.raw08 & 0xfffff000u) + 4096u) >> 12;
    state.raw4c = state.raw48 * 4096u;
  } else {
    state.raw48 = (((state.raw08 & 0xffff8000u) - 32768u) >> 15) + 15u;
    state.raw4c = state.raw48 * 32768u;
  }
  // Preserve observed unsigned modulo32 arithmetic and comparison, including
  // exact-boundary and overflow behavior; do not replace with generic ceil/fit.
  if (state.raw38 >= static_cast<std::uint32_t>(state.raw30 + state.raw48))
    return 1;
  Core::DebugPrintf("[e] Firmware image is too large (size=0x%X) to fit onto "
                    "this part (id=0x%08X)\n",
                    state.raw08, state.raw18);
  return 0;
}
} // namespace Presonus
