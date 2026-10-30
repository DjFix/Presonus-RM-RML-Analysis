#include "presonus/mixer_dsp/GateParameterList.hpp"
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
GateParamList::GateParamList()
    : parameters_(presonus::dsp::DescriptorSourceTag{}) {
  parameters_.addToggle(0, "on", "Gate On", "GATE Power", fromWord(0x00000000u),
                        "", 34);
  parameters_.addToggle(1, "keylisten", "Key Listen", "GATE KeyLn",
                        fromWord(0x00000000u), "", 34);
  parameters_.addToggle(2, "expander", "Expander", "GATE Expnd",
                        fromWord(0x00000000u), "onoff", 34);
  parameters_.addFloat(3, "keyfilter", "Key Filter", "GATE Key Fltr",
                       fromWord(0x42200000u), fromWord(0x467a0000u),
                       fromWord(0x41a00000u), "freq/off", "log",
                       fromWord(0x00000000u), 34);
  parameters_.addFloat(4, "threshold", "Threshold", "GATE Thresh",
                       fromWord(0xc2a80000u), fromWord(0x00000000u),
                       fromWord(0xc2a80000u), "gain", "linear",
                       fromWord(0x00000000u), 34);
  parameters_.addFloat(5, "range", "Range", "GATE Range", fromWord(0xc2a80000u),
                       fromWord(0x00000000u), fromWord(0xc2a80000u), "gain",
                       "gaterange", fromWord(0xc1a80000u), 34);
  parameters_.addFloat(6, "attack", "Attack", "GATE Attack",
                       fromWord(0x37a7c5acu), fromWord(0x3f000000u),
                       fromWord(0x3ba3d70au), "time", "exp",
                       fromWord(0x3ba3d70au), 34);
  parameters_.addFloat(7, "release", "Release", "GATE Release",
                       fromWord(0x3d4ccccdu), fromWord(0x40000000u),
                       fromWord(0x3f333333u), "time", "skew",
                       fromWord(0x3f333333u), 34);
  parameters_.addFloat(8, "ratio", "Ratio", "", fromWord(0x00000000u),
                       fromWord(0x3dcccccdu), fromWord(0x00000000u), "", "",
                       fromWord(0x00000000u), 33);
  parameters_.addFloat(9, "reduction", "Reduction", "", fromWord(0xc2a80000u),
                       fromWord(0x00000000u), fromWord(0x00000000u), "gain",
                       "linear", fromWord(0x00000000u), 33);
}
GateParamList::~GateParamList() = default;
GateParamList *GateParamList::instance() {
  static GateParamList theInstance;
  return &theInstance;
}
} // namespace Presonus::Dsp
namespace presonus::dsp {
const Presonus::Dsp::ParamDescriptorList &
sourceList(const Presonus::Dsp::GateParamList &value) noexcept {
  return value.parameters_;
}
} // namespace presonus::dsp
