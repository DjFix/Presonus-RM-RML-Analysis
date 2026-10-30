#pragma once
#include "core/system/corethread.h"

namespace presonus::dice {
// Actual pinned CCL RAII lock; null is reserved for thread-confined
// setup/fixtures.
using ReceiverStateGuard = Core::Threads::ScopedLock;
} // namespace presonus::dice
