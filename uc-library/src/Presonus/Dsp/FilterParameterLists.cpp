#include "presonus/mixer_dsp/FilterParameterLists.hpp"
#include <cstdint>
#include <cstring>
namespace {
float fromWord(std::uint32_t v) {
  float f;
  std::memcpy(&f, &v, 4);
  return f;
}
} // namespace
namespace Presonus::Dsp {
HiPassParamList::HiPassParamList()
    : parameters_(presonus::dsp::DescriptorSourceTag{}) {
  parameters_.addFloat(0, "hpf", "Hi Pass Filter", "HI PASS Filter",
                       fromWord(0x41c00000u), fromWord(0x447a0000u),
                       fromWord(0x41c00000u), "freq.0/off", "log",
                       fromWord(0x00000000u), 2);
}
HiPassParamList::~HiPassParamList() = default;
HiPassParamList *HiPassParamList::instance() {
  static HiPassParamList theInstance;
  return &theInstance;
}
LoPassParamList::LoPassParamList()
    : parameters_(presonus::dsp::DescriptorSourceTag{}) {
  parameters_.addFloat(0, "lpf", "Lo Pass Filter", nullptr,
                       fromWord(0x42c80000u), fromWord(0x469c4000u),
                       fromWord(0x469c4000u), "freq.0/~/off", "log",
                       fromWord(0x00000000u), 2);
}
LoPassParamList::~LoPassParamList() = default;
LoPassParamList *LoPassParamList::instance() {
  static LoPassParamList theInstance;
  return &theInstance;
}
} // namespace Presonus::Dsp
namespace presonus::dsp {
const Presonus::Dsp::ParamDescriptorList &
sourceList(const Presonus::Dsp::HiPassParamList &v) noexcept {
  return v.parameters_;
}
const Presonus::Dsp::ParamDescriptorList &
sourceList(const Presonus::Dsp::LoPassParamList &v) noexcept {
  return v.parameters_;
}
} // namespace presonus::dsp
