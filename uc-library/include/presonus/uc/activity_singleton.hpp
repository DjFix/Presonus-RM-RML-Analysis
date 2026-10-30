#pragma once
#include "presonus/uc/network_activity_manager.hpp"

namespace presonus::uc {
// Independent source-provider entry. The singleton implementation itself comes
// from the unmodified pinned CCL macro/template. No original app instance()
// declaration, native private layout or Core firmware body is reconstructed.
Presonus::UC::NetworkActivityManager &sourceActivitySingleton();
} // namespace presonus::uc
