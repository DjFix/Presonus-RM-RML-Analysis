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
  float getPeakHold() const;
  void reset();
  float getDecayDelta() const;
  float getPeakDecayDelta() const;

private:
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
  const MeterDecayTable *decayTable_ = nullptr;
};
} // namespace Presonus
