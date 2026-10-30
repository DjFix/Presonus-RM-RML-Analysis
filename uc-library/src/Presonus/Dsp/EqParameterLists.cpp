#include "presonus/mixer_dsp/EqParameterLists.hpp"
#include <cstdint>
#include <cstring>
namespace Presonus::Dsp {
// Original internal data identities retained. Native pointer width, const
// spelling and source object layout are source-port choices, not ARM ABI.
static const char *EQTypeList[] = {"Hi Pass", "Low Shelf", "Hi Shelf",
                                   "Parametric"};
static const char *Eq8ExtTypeList[] = {"Bell",      "Notch",      "All Pass",
                                       "Low Shelf", "High Shelf", "Band Pass",
                                       "High Pass", "Low Pass"};
} // namespace Presonus::Dsp
namespace {
float fromWord(std::uint32_t value) {
  float result;
  std::memcpy(&result, &value, sizeof result);
  return result;
}
void initializeEqParamList(Presonus::Dsp::ParamDescriptorList &list) {
  list.addToggle(0, "eqallon", "EQ On", "EQ Power", fromWord(0x3f800000u), "",
                 2);
  list.addList(1, "eqtype1", "EQ Type 1", nullptr, Presonus::Dsp::EQTypeList, 4,
               fromWord(0x3f800000u), 1);
  list.addFloat(2, "eqgain1", "EQ Gain 1", nullptr, fromWord(0xc1700000u),
                fromWord(0x41700000u), fromWord(0x00000000u), "gain", "linear",
                fromWord(0x00000000u), 18);
  list.addFloat(3, "eqq1", "EQ Q 1", nullptr, fromWord(0x3dcccccdu),
                fromWord(0x40800000u), fromWord(0x3f19999au), "", "skew",
                fromWord(0x3f19999au), 2);
  list.addFloat(4, "eqfreq1", "EQ Freq 1", nullptr, fromWord(0x42100000u),
                fromWord(0x43e88000u), fromWord(0x43020000u), "freq", "log",
                fromWord(0x00000000u), 2);
  list.addToggle(5, "eqbandon1", "EQ On 1", nullptr, fromWord(0x00000000u), "",
                 2);
  list.addToggle(6, "eqbandop1", "EQ Opt 1", nullptr, fromWord(0x00000000u), "",
                 2);
  list.addList(7, "eqtype2", "EQ Type 2", nullptr, Presonus::Dsp::EQTypeList, 4,
               fromWord(0x40400000u), 1);
  list.addFloat(8, "eqgain2", "EQ Gain 2", nullptr, fromWord(0xc1700000u),
                fromWord(0x41700000u), fromWord(0x00000000u), "gain", "linear",
                fromWord(0x00000000u), 18);
  list.addFloat(9, "eqq2", "EQ Q 2", nullptr, fromWord(0x3dcccccdu),
                fromWord(0x40800000u), fromWord(0x3f19999au), "", "skew",
                fromWord(0x3f19999au), 2);
  list.addFloat(10, "eqfreq2", "EQ Freq 2", nullptr, fromWord(0x42b40000u),
                fromWord(0x44960000u), fromWord(0x43a00000u), "freq", "log",
                fromWord(0x00000000u), 2);
  list.addToggle(11, "eqbandon2", "EQ On 2", nullptr, fromWord(0x00000000u), "",
                 2);
  list.addToggle(12, "eqbandop2", "EQ Opt 2", nullptr, fromWord(0x00000000u),
                 "", 0);
  list.addList(13, "eqtype3", "EQ Type 3", nullptr, Presonus::Dsp::EQTypeList,
               4, fromWord(0x40400000u), 1);
  list.addFloat(14, "eqgain3", "EQ Gain 3", nullptr, fromWord(0xc1700000u),
                fromWord(0x41700000u), fromWord(0x00000000u), "gain", "linear",
                fromWord(0x00000000u), 18);
  list.addFloat(15, "eqq3", "EQ Q 3", nullptr, fromWord(0x3dcccccdu),
                fromWord(0x40800000u), fromWord(0x3f19999au), "", "skew",
                fromWord(0x3f19999au), 2);
  list.addFloat(16, "eqfreq3", "EQ Freq 3", nullptr, fromWord(0x43be0000u),
                fromWord(0x459c4000u), fromWord(0x44af0000u), "freq", "log",
                fromWord(0x00000000u), 2);
  list.addToggle(17, "eqbandon3", "EQ On 3", nullptr, fromWord(0x00000000u), "",
                 2);
  list.addToggle(18, "eqbandop3", "EQ Opt 3", nullptr, fromWord(0x00000000u),
                 "", 0);
  list.addList(19, "eqtype4", "EQ Type 4", nullptr, Presonus::Dsp::EQTypeList,
               4, fromWord(0x40000000u), 1);
  list.addFloat(20, "eqgain4", "EQ Gain 4", nullptr, fromWord(0xc1700000u),
                fromWord(0x41700000u), fromWord(0x00000000u), "gain", "linear",
                fromWord(0x00000000u), 18);
  list.addFloat(21, "eqq4", "EQ Q 4", nullptr, fromWord(0x3dcccccdu),
                fromWord(0x40800000u), fromWord(0x3f19999au), "", "skew",
                fromWord(0x3f19999au), 2);
  list.addFloat(22, "eqfreq4", "EQ Freq 4", nullptr, fromWord(0x44af0000u),
                fromWord(0x468ca000u), fromWord(0x459c4000u), "freq", "log",
                fromWord(0x00000000u), 2);
  list.addToggle(23, "eqbandon4", "EQ On 4", nullptr, fromWord(0x00000000u), "",
                 2);
  list.addToggle(24, "eqbandop4", "EQ Opt 4", nullptr, fromWord(0x00000000u),
                 "", 2);
}
void initializeEq8ExtParamList(Presonus::Dsp::ParamDescriptorList &list) {
  list.addToggle(0, "eqallon", "EQ On", nullptr, fromWord(0x00000000u), "", 2);
  list.addList(1, "eqtype1", "EQ Type 1", nullptr,
               Presonus::Dsp::Eq8ExtTypeList, 8, fromWord(0x00000000u), 2);
  list.addFloat(2, "eqgain1", "EQ Gain 1", nullptr, fromWord(0xc1700000u),
                fromWord(0x41700000u), fromWord(0x00000000u), "gain", "",
                fromWord(0x00000000u), 2);
  list.addFloat(3, "eqq1", "Q 1", nullptr, fromWord(0x3dcccccdu),
                fromWord(0x41480000u), fromWord(0x3f800000u), "eqq", "skew",
                fromWord(0x3f800000u), 2);
  list.addFloat(4, "eqfreq1", "EQ Freq 1", nullptr, fromWord(0x41a00000u),
                fromWord(0x469c4000u), fromWord(0x42700000u), "freq", "log",
                fromWord(0x00000000u), 2);
  list.addToggle(5, "eqbandon1", "Band On 1", nullptr, fromWord(0x00000000u),
                 "", 2);
  list.addToggle(6, "eqbandop1", "Band Option 1", nullptr,
                 fromWord(0x00000000u), "", 2);
  list.addList(7, "eqtype2", "EQ Type 2", nullptr,
               Presonus::Dsp::Eq8ExtTypeList, 8, fromWord(0x00000000u), 2);
  list.addFloat(8, "eqgain2", "EQ Gain 2", nullptr, fromWord(0xc1700000u),
                fromWord(0x41700000u), fromWord(0x00000000u), "gain", "",
                fromWord(0x00000000u), 2);
  list.addFloat(9, "eqq2", "Q 2", nullptr, fromWord(0x3dcccccdu),
                fromWord(0x41480000u), fromWord(0x3f800000u), "eqq", "skew",
                fromWord(0x3f800000u), 2);
  list.addFloat(10, "eqfreq2", "EQ Freq 2", nullptr, fromWord(0x41a00000u),
                fromWord(0x469c4000u), fromWord(0x42f00000u), "freq", "log",
                fromWord(0x00000000u), 2);
  list.addToggle(11, "eqbandon2", "Band On 2", nullptr, fromWord(0x00000000u),
                 "", 2);
  list.addToggle(12, "eqbandop2", "Band Option 2", nullptr,
                 fromWord(0x00000000u), "", 2);
  list.addList(13, "eqtype3", "EQ Type 3", nullptr,
               Presonus::Dsp::Eq8ExtTypeList, 8, fromWord(0x00000000u), 2);
  list.addFloat(14, "eqgain3", "EQ Gain 3", nullptr, fromWord(0xc1700000u),
                fromWord(0x41700000u), fromWord(0x00000000u), "gain", "",
                fromWord(0x00000000u), 2);
  list.addFloat(15, "eqq3", "Q 3", nullptr, fromWord(0x3dcccccdu),
                fromWord(0x41480000u), fromWord(0x3f800000u), "eqq", "skew",
                fromWord(0x3f800000u), 2);
  list.addFloat(16, "eqfreq3", "EQ Freq 3", nullptr, fromWord(0x41a00000u),
                fromWord(0x469c4000u), fromWord(0x43700000u), "freq", "log",
                fromWord(0x00000000u), 2);
  list.addToggle(17, "eqbandon3", "Band On 3", nullptr, fromWord(0x00000000u),
                 "", 2);
  list.addToggle(18, "eqbandop3", "Band Option 3", nullptr,
                 fromWord(0x00000000u), "", 2);
  list.addList(19, "eqtype4", "EQ Type 4", nullptr,
               Presonus::Dsp::Eq8ExtTypeList, 8, fromWord(0x00000000u), 2);
  list.addFloat(20, "eqgain4", "EQ Gain 4", nullptr, fromWord(0xc1700000u),
                fromWord(0x41700000u), fromWord(0x00000000u), "gain", "",
                fromWord(0x00000000u), 2);
  list.addFloat(21, "eqq4", "Q 4", nullptr, fromWord(0x3dcccccdu),
                fromWord(0x41480000u), fromWord(0x3f800000u), "eqq", "skew",
                fromWord(0x3f800000u), 2);
  list.addFloat(22, "eqfreq4", "EQ Freq 4", nullptr, fromWord(0x41a00000u),
                fromWord(0x469c4000u), fromWord(0x43f00000u), "freq", "log",
                fromWord(0x00000000u), 2);
  list.addToggle(23, "eqbandon4", "Band On 4", nullptr, fromWord(0x00000000u),
                 "", 2);
  list.addToggle(24, "eqbandop4", "Band Option 4", nullptr,
                 fromWord(0x00000000u), "", 2);
  list.addList(25, "eqtype5", "EQ Type 5", nullptr,
               Presonus::Dsp::Eq8ExtTypeList, 8, fromWord(0x00000000u), 2);
  list.addFloat(26, "eqgain5", "EQ Gain 5", nullptr, fromWord(0xc1700000u),
                fromWord(0x41700000u), fromWord(0x00000000u), "gain", "",
                fromWord(0x00000000u), 2);
  list.addFloat(27, "eqq5", "Q 5", nullptr, fromWord(0x3dcccccdu),
                fromWord(0x41480000u), fromWord(0x3f800000u), "eqq", "skew",
                fromWord(0x3f800000u), 2);
  list.addFloat(28, "eqfreq5", "EQ Freq 5", nullptr, fromWord(0x41a00000u),
                fromWord(0x469c4000u), fromWord(0x44700000u), "freq", "log",
                fromWord(0x00000000u), 2);
  list.addToggle(29, "eqbandon5", "Band On 5", nullptr, fromWord(0x00000000u),
                 "", 2);
  list.addToggle(30, "eqbandop5", "Band Option 5", nullptr,
                 fromWord(0x00000000u), "", 2);
  list.addList(31, "eqtype6", "EQ Type 6", nullptr,
               Presonus::Dsp::Eq8ExtTypeList, 8, fromWord(0x00000000u), 2);
  list.addFloat(32, "eqgain6", "EQ Gain 6", nullptr, fromWord(0xc1700000u),
                fromWord(0x41700000u), fromWord(0x00000000u), "gain", "",
                fromWord(0x00000000u), 2);
  list.addFloat(33, "eqq6", "Q 6", nullptr, fromWord(0x3dcccccdu),
                fromWord(0x41480000u), fromWord(0x3f800000u), "eqq", "skew",
                fromWord(0x3f800000u), 2);
  list.addFloat(34, "eqfreq6", "EQ Freq 6", nullptr, fromWord(0x41a00000u),
                fromWord(0x469c4000u), fromWord(0x44f00000u), "freq", "log",
                fromWord(0x00000000u), 2);
  list.addToggle(35, "eqbandon6", "Band On 6", nullptr, fromWord(0x00000000u),
                 "", 2);
  list.addToggle(36, "eqbandop6", "Band Option 6", nullptr,
                 fromWord(0x00000000u), "", 2);
  list.addList(37, "eqtype7", "EQ Type 7", nullptr,
               Presonus::Dsp::Eq8ExtTypeList, 8, fromWord(0x00000000u), 2);
  list.addFloat(38, "eqgain7", "EQ Gain 7", nullptr, fromWord(0xc1700000u),
                fromWord(0x41700000u), fromWord(0x00000000u), "gain", "",
                fromWord(0x00000000u), 2);
  list.addFloat(39, "eqq7", "Q 7", nullptr, fromWord(0x3dcccccdu),
                fromWord(0x41480000u), fromWord(0x3f800000u), "eqq", "skew",
                fromWord(0x3f800000u), 2);
  list.addFloat(40, "eqfreq7", "EQ Freq 7", nullptr, fromWord(0x41a00000u),
                fromWord(0x469c4000u), fromWord(0x45700000u), "freq", "log",
                fromWord(0x00000000u), 2);
  list.addToggle(41, "eqbandon7", "Band On 7", nullptr, fromWord(0x00000000u),
                 "", 2);
  list.addToggle(42, "eqbandop7", "Band Option 7", nullptr,
                 fromWord(0x00000000u), "", 2);
  list.addList(43, "eqtype8", "EQ Type 8", nullptr,
               Presonus::Dsp::Eq8ExtTypeList, 8, fromWord(0x00000000u), 2);
  list.addFloat(44, "eqgain8", "EQ Gain 8", nullptr, fromWord(0xc1700000u),
                fromWord(0x41700000u), fromWord(0x00000000u), "gain", "",
                fromWord(0x00000000u), 2);
  list.addFloat(45, "eqq8", "Q 8", nullptr, fromWord(0x3dcccccdu),
                fromWord(0x41480000u), fromWord(0x3f800000u), "eqq", "skew",
                fromWord(0x3f800000u), 2);
  list.addFloat(46, "eqfreq8", "EQ Freq 8", nullptr, fromWord(0x41a00000u),
                fromWord(0x469c4000u), fromWord(0x45f00000u), "freq", "log",
                fromWord(0x00000000u), 2);
  list.addToggle(47, "eqbandon8", "Band On 8", nullptr, fromWord(0x00000000u),
                 "", 2);
  list.addToggle(48, "eqbandop8", "Band Option 8", nullptr,
                 fromWord(0x00000000u), "", 2);
}
} // namespace
namespace Presonus::Dsp {
EqParamList::EqParamList() : parameters_(presonus::dsp::DescriptorSourceTag{}) {
  initializeEqParamList(parameters_);
}
EqParamList::~EqParamList() = default;
EqParamList *EqParamList::instance() {
  static EqParamList theInstance;
  return &theInstance;
}
Eq8ExtParamList::Eq8ExtParamList()
    : parameters_(presonus::dsp::DescriptorSourceTag{}) {
  initializeEq8ExtParamList(parameters_);
}
Eq8ExtParamList::~Eq8ExtParamList() = default;
Eq8ExtParamList *Eq8ExtParamList::instance() {
  static Eq8ExtParamList theInstance;
  return &theInstance;
}
} // namespace Presonus::Dsp
namespace presonus::dsp {
const Presonus::Dsp::ParamDescriptorList &
sourceList(const Presonus::Dsp::EqParamList &value) noexcept {
  return value.parameters_;
}
const Presonus::Dsp::ParamDescriptorList &
sourceList(const Presonus::Dsp::Eq8ExtParamList &value) noexcept {
  return value.parameters_;
}
} // namespace presonus::dsp
