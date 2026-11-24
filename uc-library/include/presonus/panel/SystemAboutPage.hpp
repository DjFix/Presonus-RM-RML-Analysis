#pragma once
#include "core/portable/coreparams.h"
#include "presonus/panel/Page.hpp"
namespace Presonus::Panel {
// Portable model of the qualified Page teardown and borrowed store parameter.
// Original construction, layout and ordinary return remain unresolved.
class SystemAboutPage : public Page {
public:
  explicit SystemAboutPage(Core::Portable::NumericParam *parameter = nullptr)
      : storeParameter(parameter) {}
  SystemAboutPage(Page::Elements elements,
                  Core::Portable::NumericParam *parameter);
  ~SystemAboutPage() override;
  void store() override;
  // Independent borrowed binding. Caller keeps parameter valid for both calls
  // and does not replace or destroy it from synchronous parameter callbacks.
  void bindStoreParameter(Core::Portable::NumericParam *parameter) {
    storeParameter = parameter;
  }

private:
  Core::Portable::NumericParam *storeParameter;
};
} // namespace Presonus::Panel
