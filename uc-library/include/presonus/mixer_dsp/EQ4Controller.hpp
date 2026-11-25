#pragma once

#include "presonus/mixer_dsp/Dsp.hpp"
#include <array>

namespace Presonus::Dsp {

// Typed source view of the observed four-band property sent to the CCL
// handler. The original C++ payload type and object layout remain unresolved.
struct EQ4CoefficientsProperty : Core::Property {
  static constexpr Core::PropertyType kID = FOUR_CHAR_ID('i', 'i', 'r', '4');

  int channel = 0;
  float gain = 1.f;
  std::array<float, 4> firstNumerator{};
  std::array<float, 4> secondNumerator{};
  std::array<float, 4> firstFeedback{};
  std::array<float, 4> secondFeedback{};

  EQ4CoefficientsProperty() : Property(kID, sizeof(EQ4CoefficientsProperty)) {}
};

// Inheritance is based on the original RTTI. The host class is a source port.
class EQ4Controller : public EQController {
public:
  explicit EQ4Controller(int);
  ~EQ4Controller() override;

  // Void follows the portable base contract. The original return declaration
  // remains unresolved.
  void doUpdates() override;
};

} // namespace Presonus::Dsp
