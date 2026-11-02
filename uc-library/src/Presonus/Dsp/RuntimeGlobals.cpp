#include "presonus/dsp/RuntimeGlobals.hpp"
#include <stdexcept>

namespace {
thread_local presonus::dsp::RuntimeMemory binding{};
std::uint32_t read(std::uint32_t address) {
  if (!binding.read32)
    throw std::logic_error("runtime guest-memory binding missing");
  return binding.read32(binding.context, address);
}
} // namespace
namespace presonus::dsp {
void bindRuntimeMemory(RuntimeMemory memory) {
  if (!memory.read32 || !memory.write32)
    throw std::invalid_argument("runtime requires read32 and write32");
  binding = memory;
}
} // namespace presonus::dsp
namespace Presonus::Dsp {
std::uint32_t getAudioHAL() { return read(read(0x494054U) + 0x1cU) + 0xb0U; }
} // namespace Presonus::Dsp
extern "C" std::uint32_t getSharedLink() { return read(0x49db64U); }
extern "C" std::uint32_t getDSPState() {
  const auto link = read(0x49db64U);
  return link ? read(link + 0x3decU) : 0xffffffffU;
}
extern "C" std::uint32_t isLinkReady() {
  const auto link = read(0x49db64U);
  return link && read(link + 0x3df4U) == 0xbadb100dU ? 1U : 0U;
}
extern "C" void shutdownDSP() {
  const auto link = read(0x49db64U);
  if (link)
    binding.write32(binding.context, link + 0x3df0U, 1U);
}
