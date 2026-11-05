#pragma once
#include "core/public/coreproperty.h"
#include "presonus/mixer_dsp/ParamDescriptorList.hpp"
namespace presonus::dsp {
// Independent source-port construction and state. No original ARM layout,
// ownership, inheritance, constructor or unencoded return type is asserted.
struct ControllerSourceTag {};
struct ControllerSourceState {
  const Core::ConstVector<Presonus::Dsp::ParamDescriptor *> *descriptors =
      nullptr;
  bool lookupByTag = false;
  // Named source-port slots reflect constructor stores, not original fields.
  const Presonus::Dsp::ParamDescriptorList *descriptorList = nullptr;
  std::uint32_t word04 = 0, word08 = 0xffffffffu;
  std::uint32_t word10 = 0, word14 = 0, word20 = 0;
  int constructorId = 0; // observed input at native +0x18
  std::uint8_t byte1d = 0;
  // Independent storage for observed +0x1c and +0x24 state, not ARM layout.
  std::uint8_t processDirty = 0;
  std::uint32_t processRateBits = 0;
  Core::IPropertyHandler *handler = nullptr, *target = nullptr;
};
} // namespace presonus::dsp
namespace Presonus {
struct StringResult;
}
namespace Presonus::Dsp {
struct ParamInfo;
struct SetupProperty;
struct ChannelProperty;
class Controller {
public:
  explicit Controller(presonus::dsp::ControllerSourceTag) {}
  Controller(int, const ParamDescriptorList *);
  virtual ~Controller();
  virtual void setProperty(const Core::Property &);
  void sendProperty(Core::Property &);
  void sendProperty(ChannelProperty &, bool);
  virtual void setHandler(Core::IPropertyHandler *);
  virtual void setTarget(Core::IPropertyHandler *);
  void makeTargetOwner();
  virtual void release();
  void setDefaultValues();
  int canFloatPrecision(int) const;
  int canConfiguration(int, int) const;
  virtual int canSetup(const SetupProperty &) const;
  int usedInProcessContext() const;
  virtual int getNumParameters() const;
  virtual unsigned flushParameterChanges();
  virtual void doUpdates() = 0; // unmapped base default remains unresolved
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
  // Portable source contracts; original ordinary return declarations pending.
  virtual void printValue(Presonus::StringResult &, int, float) const;
  virtual void getParameterInfo(ParamInfo &, int) const;
  virtual bool scanValue(float &, int, const char *) const;
  // Portable void contract; original return declaration remains unresolved.
  // property must borrow at least 12 readable bytes; +8 is the observed word.
  virtual void setupProcess(const SetupProperty &property);

private:
  const ParamDescriptor &descriptor(int) const;
  presonus::dsp::ControllerSourceState state_;
};
} // namespace Presonus::Dsp
