#pragma once
#include "presonus/dsp/Controller.hpp"
#include "presonus/dsp/biquad_calc.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <memory>
#include <span>

namespace presonus::dsp {
// Independent source-port storage. Offsets identify observed ARM memory
// accesses, not a recovered class layout. No original ABI is
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
class SLReverbController : public Controller {
public:
  explicit SLReverbController(int);
  explicit SLReverbController(presonus::dsp::ReverbPortState &state);
  // Controller::setValue remains pure: its distinct native behavior is outside
  // this constructor recovery. A boundary implementation belongs to the caller.
  presonus::dsp::ReverbPortState &reverbSourceState() { return state_; }
  const presonus::dsp::ReverbPortState &reverbSourceState() const {
    return state_;
  }
  const DSP::BiquadCalc<double, false> *reverbBiquad() const {
    return biquad_.get();
  }
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
  // Owned constructor state and borrowed legacy state share exactly the same
  // method storage; host references/ownership are intentional source-port APIs.
  std::unique_ptr<presonus::dsp::ReverbPortState> ownedState_;
  presonus::dsp::ReverbPortState &state_;
  std::unique_ptr<DSP::BiquadCalc<double, false>> biquad_;
  std::uint32_t word(std::size_t) const;
  float scalar(std::size_t) const;
  void store(std::size_t, std::uint32_t);
  float preset(std::size_t) const;
  std::uint32_t presetWord(std::size_t) const;
  void dependency(std::uint32_t, std::array<std::uint32_t, 4>);
  void coefficients(std::size_t, float, bool = true);
};
} // namespace Presonus::Dsp
