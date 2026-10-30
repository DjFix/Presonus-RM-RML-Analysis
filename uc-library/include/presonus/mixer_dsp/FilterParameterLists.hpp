#pragma once
#include "presonus/mixer_dsp/ParamDescriptorList.hpp"
namespace Presonus::Dsp {
class HiPassParamList;
class LoPassParamList;
} // namespace Presonus::Dsp
namespace presonus::dsp {
const Presonus::Dsp::ParamDescriptorList &
sourceList(const Presonus::Dsp::HiPassParamList &) noexcept;
const Presonus::Dsp::ParamDescriptorList &
sourceList(const Presonus::Dsp::LoPassParamList &) noexcept;
} // namespace presonus::dsp
namespace Presonus::Dsp {
// Modern composition only; original inheritance/layout unproved.
class HiPassParamList {
public:
  HiPassParamList();
  ~HiPassParamList();
  HiPassParamList(const HiPassParamList &) = delete;
  HiPassParamList &operator=(const HiPassParamList &) = delete;
  // Original return/static declaration unresolved.
  static HiPassParamList *instance();

private:
  friend const ParamDescriptorList &
  presonus::dsp::sourceList(const HiPassParamList &) noexcept;
  ParamDescriptorList parameters_;
};
// Modern composition only; original inheritance/layout unproved.
class LoPassParamList {
public:
  LoPassParamList();
  ~LoPassParamList();
  LoPassParamList(const LoPassParamList &) = delete;
  LoPassParamList &operator=(const LoPassParamList &) = delete;
  // Original return/static declaration unresolved.
  static LoPassParamList *instance();

private:
  friend const ParamDescriptorList &
  presonus::dsp::sourceList(const LoPassParamList &) noexcept;
  ParamDescriptorList parameters_;
};
} // namespace Presonus::Dsp
