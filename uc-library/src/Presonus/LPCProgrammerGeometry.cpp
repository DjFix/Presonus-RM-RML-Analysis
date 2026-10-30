#include "presonus/application/LPCProgrammerGeometry.hpp"
#include "core/system/coredebug.h"

namespace Presonus {
unsigned LPCProgrammer::getLastSector(unsigned part) {
  switch (part) {
  case 620838711u:
  case 637615927u:
  case 638664503u:
  case 637610039u:
    return 29;
  case 637613875u:
  case 620828451u:
  case 637615923u:
    return 21;
  case 620761377u:
  case 436340005u:
    return 15;
  case 637606178u:
  case 620828450u:
    return 17;
  case 620761368u:
    return 7;
  default:
    Core::DebugPrintf("[e] Unknown part id (%08x)\n", part);
    return 0;
  }
}
} // namespace Presonus
