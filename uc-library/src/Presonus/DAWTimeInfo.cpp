#include "presonus/DAWTimeInfo.hpp"

namespace Presonus {

unsigned int DAWTimeInfo::isMusicalDisplay() const {
  if (sourceState_)
    return static_cast<unsigned int>(sourceState_->musicalDisplay);
  return borrowedState_[0x134];
}

} // namespace Presonus
