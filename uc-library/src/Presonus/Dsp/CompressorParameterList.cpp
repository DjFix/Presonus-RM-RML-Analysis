#include "presonus/mixer_dsp/CompressorParameterList.hpp"
#include <cstdint>
#include <cstring>
namespace {
float fromWord(std::uint32_t word) {
  float value;
  std::memcpy(&value, &word, 4);
  return value;
}
} // namespace
namespace Presonus::Dsp {
CompressorParamList::CompressorParamList()
    : parameters_(presonus::dsp::DescriptorSourceTag{}) {
  parameters_.addToggle(0, "on", "Compressor On", "COMP Power",
                        fromWord(0x00000000u), "", 34);
  parameters_.addToggle(1, "softknee", "Soft Knee", "COMP Soft",
                        fromWord(0x00000000u), "", 34);
  parameters_.addToggle(2, "automode", "Auto", "COMP Auto",
                        fromWord(0x00000000u), "", 34);
  parameters_.addFloat(3, "threshold", "Threshold", "COMP Thresh",
                       fromWord(0xc2600000u), fromWord(0x00000000u),
                       fromWord(0x00000000u), "gain", "linear",
                       fromWord(0x00000000u), 34);
  parameters_.addFloat(4, "ratio", "Ratio", "COMP Ratio", fromWord(0x3f800000u),
                       fromWord(0x41a00000u), fromWord(0x40000000u),
                       "ratio/~/limit", "ratio", fromWord(0x40000000u), 34);
  parameters_.addFloat(5, "attack", "Attack", "COMP Attack",
                       fromWord(0x3951b717u), fromWord(0x3e19999au),
                       fromWord(0x3ca3d70au), "time", "skew",
                       fromWord(0x3ca3d70au), 34);
  parameters_.addFloat(6, "release", "Release", "COMP Release",
                       fromWord(0x3b23d70au), fromWord(0x3f666666u),
                       fromWord(0x3e19999au), "time", "skew",
                       fromWord(0x3e19999au), 34);
  parameters_.addFloat(7, "gain", "Gain", "COMP Gain", fromWord(0x00000000u),
                       fromWord(0x41e00000u), fromWord(0x00000000u), "gain",
                       "linear", fromWord(0x00000000u), 34);
  parameters_.addFloat(8, "reduction", "Reduction", "", fromWord(0xc1a80000u),
                       fromWord(0x00000000u), fromWord(0x00000000u), "gain",
                       "linear", fromWord(0x00000000u), 33);
  parameters_.addFloat(9, "kneewidth", "Knee Width", "", fromWord(0x00000000u),
                       fromWord(0x40400000u), fromWord(0x00000000u), "gain", "",
                       fromWord(0x00000000u), 33);
}
CompressorParamList::~CompressorParamList() = default;
CompressorParamList *CompressorParamList::instance() {
  static CompressorParamList theInstance;
  return &theInstance;
}
} // namespace Presonus::Dsp
namespace presonus::dsp {
const Presonus::Dsp::ParamDescriptorList &
sourceList(const Presonus::Dsp::CompressorParamList &value) noexcept {
  return value.parameters_;
}
} // namespace presonus::dsp
