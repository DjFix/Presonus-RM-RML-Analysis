#pragma once

#include <array>
#include <cstdint>

namespace presonus::meter {
struct MeterStateAccess;
}

namespace Presonus {
class MeterBallistics {
public:
  // Portable view of the closed constructor output. The containing class
  // and original nested object layout remain unresolved.
  class MeterDecayTable {
  public:
    struct Entry {
      float amplitude;
      float normalizedInterval;
    };

    // The caller provides six readable breakpoints and a finite nonzero
    // final interval for the observed domain.
    explicit MeterDecayTable(const float *breakpoints);
    const std::array<Entry, 5> &entries() const { return entries_; }

  private:
    std::array<Entry, 5> entries_;
  };

  MeterBallistics();
  virtual ~MeterBallistics();
  virtual float setLevel(float);
  float idleSetLevel(float);
  // Source-port return follows idleSetLevel; original return declaration is
  // unresolved.
  float idle();
  // Independent source-port configuration; no original method/ABI credit.
  void configureSourcePortDecayRate(float rate) noexcept {
    state_.decayRate = rate;
  }
  // The original base has pure virtual effect slots. Concrete storage here is
  // an independent portable compatibility policy for existing direct users.
  struct Effects {
    float meter = 0.f;
    float peak = 0.f;
    bool clipped = false;
    bool signal = false;
  };
  const Effects &effects() const noexcept { return effects_; }
  virtual bool isClipped() const;
  virtual void setClipped(bool);
  virtual void setSignal(bool);
  virtual void setMeter(float);
  virtual void setPeak(float);
  float getPeakHold() const;
  void reset();
  float getDecayDelta() const;
  float getPeakDecayDelta() const;

protected:
  // Zero-credit typed source-port construction policy; no original layout
  // claim.
  enum class DecayTablePolicy { Default, None };
  explicit MeterBallistics(DecayTablePolicy);

private:
  friend class MeterManager;
  friend struct presonus::meter::MeterStateAccess;
  struct State {
    bool mode = false;
    float scale = 1.0f;
    float decayRate = 0.04f;
    bool active = true;
    float amplitude = 0.0f;
    float peakHold = 0.0f;
    std::array<std::uint32_t, 4> auxiliary{};
  };
  State state_;
  Effects effects_;
  const MeterDecayTable *decayTable_ = nullptr;
};
} // namespace Presonus
