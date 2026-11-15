#pragma once
namespace Presonus::Mixer {
// Partial portable source port. Original bases, layout and return declaration
// are unresolved; this member needs no object state. int is a source choice.
class MicLineComponent {
public:
  int calculateDigitalMicPreampGainDivision(float *preamp, float *residual,
                                            float gain);
};
} // namespace Presonus::Mixer
