#pragma once
#include "presonus/dsp/IController.hpp"
#include "presonus/mixer_dsp/ParamDescriptorList.hpp"
namespace presonus::dsp {
// Independent source-port construction and state. No original ARM layout,
// ownership, constructor or unencoded return type is asserted.
// Interface ancestry is a source port supported by original RTTI, not ABI
// proof.
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
class Controller : public IController {
public:
  explicit Controller(presonus::dsp::ControllerSourceTag) {}
  Controller(int, const ParamDescriptorList *);
  virtual ~Controller();
  void setProperty(const Core::Property &) override;
  void getProperty(Core::Property &) override;
  // Source-port void contract; original return declaration remains unresolved.
  void processIdle() override;
  void sendProperty(Core::Property &);
  void sendProperty(ChannelProperty &, bool);
  void setHandler(Core::IPropertyHandler *) override;
  void setTarget(Core::IPropertyHandler *) override;
  void makeTargetOwner();
  void release() override;
  void setDefaultValues();
  int canFloatPrecision(int) const;
  int canConfiguration(int, int) const;
  int canSetup(const SetupProperty &) const override;
  int usedInProcessContext() const;
  int getNumParameters() const override;
  unsigned flushParameterChanges() override;
  virtual void doUpdates() = 0; // unmapped base default remains unresolved
  presonus::dsp::ControllerSourceState &sourceState() { return state_; }
  const presonus::dsp::ControllerSourceState &sourceState() const {
    return state_;
  }
  // Float returns are the portable contract. Original ordinary return
  // declarations, full vtable order and binary layout remain unresolved.
  float getValue(int) const override = 0;
  float setValue(int, float) override = 0;
  float normalizedValueToRange(int, float) const override;
  float rangeToNormalizedValue(int, float) const override;
  float getNormalized(int) const override;
  float setNormalized(int, float) override;
  float boundValue(int, float) const;
  // Portable source contracts; original ordinary return declarations pending.
  void printValue(Presonus::StringResult &, int, float) const override;
  void getParameterInfo(ParamInfo &, int) const override;
  bool scanValue(float &, int, const char *) const override;
  // Portable void contract; original return declaration remains unresolved.
  // property must borrow at least 12 readable bytes; +8 is the observed word.
  virtual void setupProcess(const SetupProperty &property);

private:
  const ParamDescriptor &descriptor(int) const;
  presonus::dsp::ControllerSourceState state_;
};
} // namespace Presonus::Dsp
