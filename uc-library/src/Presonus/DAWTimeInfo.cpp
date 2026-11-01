#include "presonus/DAWTimeInfo.hpp"

namespace Presonus {

unsigned int DAWTimeInfo::isMusicalDisplay() const {
  return borrowedState_[0x134];
}

} // namespace Presonus
