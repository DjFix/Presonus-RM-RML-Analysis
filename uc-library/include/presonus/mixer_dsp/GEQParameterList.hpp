#pragma once
#include "presonus/mixer_dsp/ParamDescriptorList.hpp"
namespace Presonus::Dsp {
class GEQParamList;
}
namespace presonus::dsp {
// Independent source-port access, not an original method.
const Presonus::Dsp::ParamDescriptorList &
sourceList(const Presonus::Dsp::GEQParamList &) noexcept;
} // namespace presonus::dsp
namespace Presonus::Dsp {
// Intentional modern composition; original inheritance/layout unproved.
class GEQParamList {
public:
  GEQParamList();
  ~GEQParamList();
  GEQParamList(const GEQParamList &) = delete;
  GEQParamList &operator=(const GEQParamList &) = delete;
  // Original return/static spelling unresolved; portable choice stays pending.
  static GEQParamList *instance();

private:
  friend const ParamDescriptorList &
  presonus::dsp::sourceList(const GEQParamList &) noexcept;
  ParamDescriptorList parameters_;
};
} // namespace Presonus::Dsp
