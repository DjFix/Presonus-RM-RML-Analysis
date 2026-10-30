#pragma once
#include "core/public/coreinterpolator.h"
#include <cstdint>

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
};

enum EqType : int;
class EQController {
public:
  // Integer/enum return naming is unresolved; machine result is a 32-bit code.
  // Valid domain is the four original table indices, 0..3.
  static int biquadFromBandType(EqType type);

  // Partial portable interface only. Original RTTI derives this class from
  // Presonus::Dsp::Controller; that unreconstructed base, original fields,
  // full vtable and virtual destructor lifecycle are not supplied here.
  explicit EQController(presonus::dsp::EQTypePortTag) {}
  // Original slot+100 proves virtual dispatch; native partial slot differs.
  // Return int is provisional: the original ordinary return is unresolved.
  virtual int getEQType(DSP::BiquadType type) const;
  // Original slot+104: indices above3 return6; negative indices are unchecked
  // and outside the supported source-port domain. Return type unresolved.
  virtual int getBiquadType(int index) const;
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
