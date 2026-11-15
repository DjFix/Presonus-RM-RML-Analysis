#pragma once
#include "core/portable/coreparams.h"
namespace Presonus::Panel {
// Partial portable source port. This class does not model the original base
// classes, fields, construction or ARM layout. Ordinary return is unresolved.
class SystemAboutPage {
public:
  explicit SystemAboutPage(Core::Portable::NumericParam *parameter = nullptr)
      : storeParameter(parameter) {}
  void store();
  // Independent borrowed binding. Caller keeps parameter valid for both calls
  // and does not replace or destroy it from synchronous parameter callbacks.
  void bindStoreParameter(Core::Portable::NumericParam *parameter) {
    storeParameter = parameter;
  }

private:
  Core::Portable::NumericParam *storeParameter;
};
} // namespace Presonus::Panel
