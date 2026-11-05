#include "presonus/link/Messenger.hpp"
#include "core/system/coredebug.h"
DEFINE_SINGLETON(Presonus::Link::Messenger)
namespace Presonus::Link {
Messenger::Messenger() {
  Core::DebugPrintf(" Msg: MAX_PROPERTY_SIZE:%d\n", 0x300);
  Core::DebugPrintf(" Msg: SharedRegion size:%d\n", 16120);
  Core::DebugPrintf(" Msg: TargetProp size:%d\n", 792);
}
// Real member lock destruction precedes pinned Singleton matching-instance
// cleanup.
Messenger::~Messenger() = default;
void Messenger::release() { releaseRequested_ = true; }
} // namespace Presonus::Link
