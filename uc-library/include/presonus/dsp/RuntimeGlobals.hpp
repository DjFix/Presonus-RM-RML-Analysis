#pragma once
#include <cstdint>

namespace presonus::dsp {
// Independent portable binding of an ARM32 guest address space. No original
// class layout, object ownership or host-pointer representation is declared.
struct RuntimeMemory {
  void *context;
  std::uint32_t (*read32)(void *, std::uint32_t);
  void (*write32)(void *, std::uint32_t, std::uint32_t);
};
// Per-thread binding; caller owns its lifetime. Throws when callbacks are
// absent.
void bindRuntimeMemory(RuntimeMemory memory);
} // namespace presonus::dsp

namespace Presonus::Dsp {
// Source-port register-word result; original pointer/reference return
// unresolved.
std::uint32_t getAudioHAL();
} // namespace Presonus::Dsp
// Source-port declarations preserving original C symbol identities. Original
// parameter and return declarations remain unresolved; these model observed
// guest-memory effects only. shutdownDSP does not operate a physical device.
extern "C" {
std::uint32_t getSharedLink();
std::uint32_t getDSPState();
std::uint32_t isLinkReady();
void shutdownDSP();
}
