#pragma once
#include "core/public/coreinterpolator.h"
#include "presonus/dsp/Controller.hpp"
#include "presonus/dsp/biquad_calc.hpp"
#include <array>
#include <cstdint>
#include <vector>

namespace DSP {
// Original qualified parameter identity is proven. Its complete declaration,
// category and underlying signedness are not; this opaque enum is a source-port
// choice, not a recovered original enum definition or ARM ABI guarantee.
enum BiquadType : int;
} // namespace DSP
namespace presonus::dsp {
// Independent tagged partial-object construction, not an original C1.
struct EQTypePortTag {};
} // namespace presonus::dsp

namespace Presonus::Dsp {
// Source-port state, deliberately independent of original ARM32 object/vtable
// layout. The original methods access these nine floats at this+4 ... this+36.
struct BilinearRecoveredState {
  float minimum = 0, maximum = 1, midpoint = .5f, reserved = 0,
        normalizedMidpoint = .5f;
  float lowSlope = 1, highSlope = 1, lowInverse = 1, highInverse = 1;
};
static_assert(sizeof(BilinearRecoveredState) == 36);

class BilinearInterpolator : public Core::Interpolator {
public:
  BilinearInterpolator();
  ~BilinearInterpolator() override;
  // Independent fixture seeding bypasses Core getter synchronization;
  // production setters synchronize actual CCL base getters. No original layout
  // claimed.
  BilinearRecoveredState &recoveredState() noexcept { return state_; }
  const BilinearRecoveredState &recoveredState() const noexcept {
    return state_;
  }
  float normalizedToRange(float value) const override;
  float rangeToNormalized(float value) const override;
  // Setter return types remain unresolved from symbol/ARM evidence. These
  // source-port declarations use void and are NOT marked signature-ready.
  void setMidPoint(float rangeMidpoint, float normalizedMidpoint);
  void setRange(float minimum, float maximum, float midpoint) override;

private:
  BilinearRecoveredState state_;
};

class ShelbyGEQController {
public:
  float denormalizeValue(float value);
  // Provisional source returns; native observes 32-bit words.
  float getValue(int index) const;
  int getNumParameters() const;
  std::array<float, 33> &portableValues() { return values_; }

private:
  std::array<float, 33> values_{};
};

// Independent portable storage for native type/three floats, calculator,
// and +0x138/+0x139/+0x13a band flags.
// It is not an original declaration or ARM layout.
struct EQBandSourceState {
  int type = 0;
  DSP::BiquadCalc<double, false> calculator;
  std::uint8_t edgeSelectable = 0;
  std::uint8_t dirty = 0;
  std::uint8_t enabled = 0;
  float frequency = 1000.f, q = .7f, gain = 0.f;
};
enum EqType : int;
class EQController : public Controller {
public:
  // Integer/enum return naming is unresolved; machine result is a 32-bit code.
  // Valid domain is the four original table indices, 0..3.
  static int biquadFromBandType(EqType type);

  // Parameter identities are original; ordinary return declarations remain
  // provisional source contracts, not original signature-readiness claims.
  int getNumBands() const;
  void triggerOption(int index);
  void setupProcess(const SetupProperty &property);
  std::vector<EQBandSourceState> &portableBands() { return bands_; }
  const std::vector<EQBandSourceState> &portableBands() const { return bands_; }
  presonus::dsp::ControllerSourceState &sourceState() {
    return controllerState_;
  }
  const presonus::dsp::ControllerSourceState &sourceState() const {
    return controllerState_;
  }
  // RTTI-supported base relationship; source storage/vtable layout is portable.
  explicit EQController(presonus::dsp::EQTypePortTag)
      : Controller(presonus::dsp::ControllerSourceTag{}),
        controllerState_(Controller::sourceState()) {}
  EQController(int, int, const ParamDescriptorList *);
  ~EQController() override;
  EQController(const EQController &) = delete;
  EQController &operator=(const EQController &) = delete;
  float getValue(int) const override;
  float setValue(int, float) override;
  void doUpdates() override;
  bool &portableEnabled() { return enabled_; }
  // Original slot+100 proves virtual dispatch; native partial slot differs.
  // Return int is provisional: the original ordinary return is unresolved.
  virtual int getEQType(DSP::BiquadType type) const;
  // Original slot+104: indices above3 return6; negative indices are unchecked
  // and outside the supported source-port domain. Return type unresolved.
  virtual int getBiquadType(int index) const;

private:
  // Reference the actual Controller source-port state. No duplicate base state;
  // the host reference/vector representation makes no original layout claim.
  presonus::dsp::ControllerSourceState &controllerState_;
  bool enabled_ = true;
  std::vector<EQBandSourceState> bands_;
};

// Original single-inheritance RTTI establishes this base relationship.
// This remains a partial portable class, not an original object ABI.
class EQ8Controller : public EQController {
public:
  explicit EQ8Controller(presonus::dsp::EQTypePortTag tag)
      : EQController(tag) {}
  int getEQType(DSP::BiquadType type) const override;
  // Indices above7 return6; negative indices remain outside supported domain.
  int getBiquadType(int index) const override;
};
} // namespace Presonus::Dsp
