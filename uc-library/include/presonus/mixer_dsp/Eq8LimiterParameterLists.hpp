#pragma once
#include "presonus/mixer_dsp/ParamDescriptorList.hpp"
namespace Presonus::Dsp {
class Eq8ParamList;
class LimiterParamList;
} // namespace Presonus::Dsp
namespace presonus::dsp {
// Independent source-port access helpers, not original methods.
const Presonus::Dsp::ParamDescriptorList &
sourceList(const Presonus::Dsp::Eq8ParamList &) noexcept;
const Presonus::Dsp::ParamDescriptorList &
sourceList(const Presonus::Dsp::LimiterParamList &) noexcept;
} // namespace presonus::dsp
namespace Presonus::Dsp {
// Explicit modern composition; original inheritance/layout unproved.
class Eq8ParamList {
public:
  Eq8ParamList();
  ~Eq8ParamList();
  Eq8ParamList(const Eq8ParamList &) = delete;
  Eq8ParamList &operator=(const Eq8ParamList &) = delete;
  // Return/static spelling remains declaration-pending.
  static Eq8ParamList *instance();

private:
  friend const ParamDescriptorList &
  presonus::dsp::sourceList(const Eq8ParamList &) noexcept;
  ParamDescriptorList parameters_;
};
// Explicit modern composition; original inheritance/layout unproved.
class LimiterParamList {
public:
  LimiterParamList();
  ~LimiterParamList();
  LimiterParamList(const LimiterParamList &) = delete;
  LimiterParamList &operator=(const LimiterParamList &) = delete;
  // Return/static spelling remains declaration-pending.
  static LimiterParamList *instance();

private:
  friend const ParamDescriptorList &
  presonus::dsp::sourceList(const LimiterParamList &) noexcept;
  ParamDescriptorList parameters_;
};
} // namespace Presonus::Dsp
