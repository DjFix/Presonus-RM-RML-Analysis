#pragma once

#include "presonus/dsp/Controller.hpp"

namespace Presonus::Dsp {

class SimpleController : public Controller {
public:
  SimpleController(int, const ParamDescriptorList *);
  ~SimpleController() override;

  float getValue(int) const override;
  // Portable return value reflects the stored value; native return declaration
  // is unresolved.
  float setValue(int, float) override;
  void setProperty(const Core::Property &) override;
  void setupProcess(const SetupProperty &) override;
  void doUpdates() override;
  void updateAll();
  virtual bool isInternal(int) const;

private:
  int findIndex(int) const;
  Core::Vector<float> values_;
  Core::Vector<int> pending_;
};

} // namespace Presonus::Dsp
