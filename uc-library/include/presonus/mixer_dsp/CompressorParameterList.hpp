#pragma once
#include "presonus/mixer_dsp/ParamDescriptorList.hpp"
namespace Presonus::Dsp {
class CompressorParamList;
}
namespace presonus::dsp {
// Independent source-port access, not an original method.
const Presonus::Dsp::ParamDescriptorList &
sourceList(const Presonus::Dsp::CompressorParamList &) noexcept;
} // namespace presonus::dsp
namespace Presonus::Dsp {
// Intentional modern composition; original inheritance/layout unproved.
class CompressorParamList {
public:
  CompressorParamList();
  ~CompressorParamList();
  CompressorParamList(const CompressorParamList &) = delete;
  CompressorParamList &operator=(const CompressorParamList &) = delete;
  // Original return/static spelling unresolved; portable choice stays pending.
  static CompressorParamList *instance();

private:
  friend const ParamDescriptorList &
  presonus::dsp::sourceList(const CompressorParamList &) noexcept;
  ParamDescriptorList parameters_;
};
} // namespace Presonus::Dsp
