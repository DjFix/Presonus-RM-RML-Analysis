#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <span>

namespace presonus::dsp {
// Independent source-port storage. Offsets identify observed ARM memory
// accesses, not a recovered class layout. No original ABI or inheritance is
// asserted.
struct ReverbPortState {
  std::array<std::byte, 1024> memory{};
  std::span<const std::byte> presets;
  std::function<int()> valueCount;
  // Required app-specific provider. Invoked with the native callee address and
  // four raw ARM argument words; implementations may update memory.
  std::function<void(std::uint32_t, std::array<std::uint32_t, 4>)> dependency;
};
} // namespace presonus::dsp
namespace Presonus::Dsp {
struct SetupProperty;
// Original namespace/signatures with deliberately independent host storage.
// Unencoded original return types remain unresolved; these are source-port
// APIs.
class SLReverbController {
public:
  explicit SLReverbController(presonus::dsp::ReverbPortState &state);
  void setDirty();
  void updateFilters();
  void calcParams(int);
  void updateDiffusor();
  void setReverbValue(int, float);
  void updateDelayFilters();
  float getValue(int) const;
  void updateFDN();
  void setupProcess(const SetupProperty &);
  void updateEarlyRefs();

private:
  presonus::dsp::ReverbPortState &state_;
  std::uint32_t word(std::size_t) const;
  float scalar(std::size_t) const;
  void store(std::size_t, std::uint32_t);
  float preset(std::size_t) const;
  std::uint32_t presetWord(std::size_t) const;
  void dependency(std::uint32_t, std::array<std::uint32_t, 4>);
  void coefficients(std::size_t, float, bool = true);
};
} // namespace Presonus::Dsp
