#pragma once
#include "presonus/mixer_dsp/ParamDescriptorList.hpp"
namespace presonus::dsp {
// Independent source-port construction and state. No original ARM layout,
// ownership, inheritance, constructor or unencoded return type is asserted.
struct ControllerSourceTag {};
struct ControllerSourceState {
  const Core::ConstVector<Presonus::Dsp::ParamDescriptor *> *descriptors =
      nullptr;
  bool lookupByTag = false;
};
} // namespace presonus::dsp
namespace Presonus::Dsp {
class Controller {
public:
  explicit Controller(presonus::dsp::ControllerSourceTag) {}
  virtual ~Controller() = default;
  presonus::dsp::ControllerSourceState &sourceState() { return state_; }
  const presonus::dsp::ControllerSourceState &sourceState() const {
    return state_;
  }
  // Float returns are the portable contract. Original ordinary return
  // declarations, full vtable order and binary layout remain unresolved.
  virtual float getValue(int) const = 0;
  virtual float setValue(int, float) = 0;
  virtual float normalizedValueToRange(int, float) const;
  virtual float rangeToNormalizedValue(int, float) const;
  float getNormalized(int) const;
  float setNormalized(int, float);
  float boundValue(int, float) const;

private:
  const ParamDescriptor &descriptor(int) const;
  presonus::dsp::ControllerSourceState state_;
};
} // namespace Presonus::Dsp
