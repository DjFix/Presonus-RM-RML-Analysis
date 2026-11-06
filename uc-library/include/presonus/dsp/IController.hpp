#pragma once
#include "core/public/coreproperty.h"
namespace Presonus {
struct StringResult;
}
namespace Presonus::Dsp {
struct ParamInfo;
struct SetupProperty;
// Application interface source port supported by original RTTI ancestry.
// Declaration order follows the observed interface slots, not a claim of ARM
// vtable layout. Ordinary return declarations use existing source contracts.
// No destructor slot is inferred; instances are disposed through release().
struct IController : Core::IPropertyHandler {
  virtual int getNumParameters() const = 0;
  virtual void getParameterInfo(ParamInfo &, int) const = 0;
  virtual float setValue(int, float) = 0;
  virtual float getValue(int) const = 0;
  virtual void printValue(Presonus::StringResult &, int, float) const = 0;
  virtual bool scanValue(float &, int, const char *) const = 0;
  virtual float normalizedValueToRange(int, float) const = 0;
  virtual float rangeToNormalizedValue(int, float) const = 0;
  virtual float setNormalized(int, float) = 0;
  virtual float getNormalized(int) const = 0;
  virtual void setHandler(Core::IPropertyHandler *) = 0;
  virtual void setTarget(Core::IPropertyHandler *) = 0;
  virtual unsigned flushParameterChanges() = 0;
  virtual void processIdle() = 0;
  virtual int canSetup(const SetupProperty &) const = 0;
};
} // namespace Presonus::Dsp
