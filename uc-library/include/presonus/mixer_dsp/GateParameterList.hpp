#pragma once
#include "presonus/mixer_dsp/ParamDescriptorList.hpp"
namespace Presonus::Dsp {
class GateParamList;
}
namespace presonus::dsp {
// Independent source-port access, not an original method.
const Presonus::Dsp::ParamDescriptorList &
sourceList(const Presonus::Dsp::GateParamList &) noexcept;
} // namespace presonus::dsp
namespace Presonus::Dsp {
// Intentional modern composition; original inheritance/layout unproved.
class GateParamList {
public:
  GateParamList();
  ~GateParamList();
  GateParamList(const GateParamList &) = delete;
  GateParamList &operator=(const GateParamList &) = delete;
  // Original return/static spelling unresolved; portable choice stays pending.
  static GateParamList *instance();

private:
  friend const ParamDescriptorList &
  presonus::dsp::sourceList(const GateParamList &) noexcept;
  ParamDescriptorList parameters_;
};
} // namespace Presonus::Dsp
