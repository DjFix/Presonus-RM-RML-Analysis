#pragma once

#include <cstdint>

// Partial portable interface. Only the observed register-width result is
// modeled. The original return declaration, class layout and vtable dispatch
// are not reconstructed by this interface.
class DSPManager {
public:
  std::uint32_t getDSPStatus();
};
