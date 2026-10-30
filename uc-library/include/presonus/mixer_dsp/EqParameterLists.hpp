#pragma once
#include "presonus/mixer_dsp/ParamDescriptorList.hpp"
namespace Presonus::Dsp {
class EqParamList;
class Eq8ExtParamList;
} // namespace Presonus::Dsp
namespace presonus::dsp {
// Independent source-port inspection helpers, not original app methods.
const Presonus::Dsp::ParamDescriptorList &
sourceList(const Presonus::Dsp::EqParamList &) noexcept;
const Presonus::Dsp::ParamDescriptorList &
sourceList(const Presonus::Dsp::Eq8ExtParamList &) noexcept;
} // namespace presonus::dsp
namespace Presonus::Dsp {
// Modern composition is intentional: original inheritance/layout unproved.
class EqParamList {
public:
  EqParamList();
  ~EqParamList();
  EqParamList(const EqParamList &) = delete;
  EqParamList &operator=(const EqParamList &) = delete;
  // Original return/static declaration remains pending.
  static EqParamList *instance();

private:
  friend const ParamDescriptorList &
  presonus::dsp::sourceList(const EqParamList &) noexcept;
  ParamDescriptorList parameters_;
};
// Modern composition is intentional: original inheritance/layout unproved.
class Eq8ExtParamList {
public:
  Eq8ExtParamList();
  ~Eq8ExtParamList();
  Eq8ExtParamList(const Eq8ExtParamList &) = delete;
  Eq8ExtParamList &operator=(const Eq8ExtParamList &) = delete;
  // Original return/static declaration remains pending.
  static Eq8ExtParamList *instance();

private:
  friend const ParamDescriptorList &
  presonus::dsp::sourceList(const Eq8ExtParamList &) noexcept;
  ParamDescriptorList parameters_;
};
} // namespace Presonus::Dsp
