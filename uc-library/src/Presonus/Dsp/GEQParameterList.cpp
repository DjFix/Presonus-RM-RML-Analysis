#include "presonus/mixer_dsp/GEQParameterList.hpp"
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
GEQParamList::GEQParamList()
    : parameters_(presonus::dsp::DescriptorSourceTag{}) {
  parameters_.addFloat(0, "gain1", "GEQ Band 1 Gain", "20 Hz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 50);
  parameters_.addFloat(1, "gain2", "GEQ Band 2 Gain", "25 Hz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 50);
  parameters_.addFloat(2, "gain3", "GEQ Band 3 Gain", "32 Hz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 50);
  parameters_.addFloat(3, "gain4", "GEQ Band 4 Gain", "40 Hz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 50);
  parameters_.addFloat(4, "gain5", "GEQ Band 5 Gain", "50 Hz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 50);
  parameters_.addFloat(5, "gain6", "GEQ Band 6 Gain", "63 Hz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 50);
  parameters_.addFloat(6, "gain7", "GEQ Band 7 Gain", "80 Hz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(7, "gain8", "GEQ Band 8 Gain", "100 Hz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(8, "gain9", "GEQ Band 9 Gain", "125 Hz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(9, "gain10", "GEQ Band 10 Gain", "160 Hz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(10, "gain11", "GEQ Band 11 Gain", "200 Hz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(11, "gain12", "GEQ Band 12 Gain", "250 Hz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(12, "gain13", "GEQ Band 13 Gain", "315 Hz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(13, "gain14", "GEQ Band 14 Gain", "400 Hz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(14, "gain15", "GEQ Band 15 Gain", "500 Hz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(15, "gain16", "GEQ Band 16 Gain", "630 Hz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(16, "gain17", "GEQ Band 17 Gain", "800 Hz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(17, "gain18", "GEQ Band 18 Gain", "1 kHz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(18, "gain19", "GEQ Band 19 Gain", "1.25 kHz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(19, "gain20", "GEQ Band 20 Gain", "1.6 kHz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(20, "gain21", "GEQ Band 21 Gain", "2 kHz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(21, "gain22", "GEQ Band 22 Gain", "2.5 kHz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(22, "gain23", "GEQ Band 23 Gain", "3.15 kHz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(23, "gain24", "GEQ Band 24 Gain", "4 kHz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(24, "gain25", "GEQ Band 25 Gain", "5 kHz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(25, "gain26", "GEQ Band 26 Gain", "6.3 kHz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(26, "gain27", "GEQ Band 27 Gain", "8 kHz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(27, "gain28", "GEQ Band 28 Gain", "10 kHz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(28, "gain29", "GEQ Band 29 Gain", "12.5 kHz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(29, "gain30", "GEQ Band 30 Gain", "16 kHz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addFloat(30, "gain31", "GEQ Band 31 Gain", "20 kHz",
                       fromWord(0xc1400000u), fromWord(0x41400000u),
                       fromWord(0x00000000u), "gain.1.value", "linear",
                       fromWord(0x00000000u), 18);
  parameters_.addToggle(31, "on", "GEQ On/Off", "", fromWord(0x00000000u), "",
                        34);
  parameters_.addToggle(32, "ston", "GEQ Stereo On/Off", "",
                        fromWord(0x3f800000u), "", 34);
}
GEQParamList::~GEQParamList() = default;
GEQParamList *GEQParamList::instance() {
  static GEQParamList theInstance;
  return &theInstance;
}
} // namespace Presonus::Dsp
namespace presonus::dsp {
const Presonus::Dsp::ParamDescriptorList &
sourceList(const Presonus::Dsp::GEQParamList &value) noexcept {
  return value.parameters_;
}
} // namespace presonus::dsp
