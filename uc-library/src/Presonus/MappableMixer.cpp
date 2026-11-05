#include "presonus/MappableMixer.hpp"

namespace Presonus {
SLChannelBase *MappableMixer::getSelectedGeq() const { return nullptr; }
int MappableMixer::countAllChannels() const { return 0; }
SLChannelBase *MappableMixer::getChannelIndexed(int) const { return nullptr; }
} // namespace Presonus
