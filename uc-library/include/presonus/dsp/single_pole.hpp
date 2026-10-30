#pragma once

namespace presonus::dsp {
// Independent public source-port entry point. The original static helper lives
// in namespace DSP and is not an exported original public interface.
float singlePole(float frequency, float sampleRate);
} // namespace presonus::dsp
