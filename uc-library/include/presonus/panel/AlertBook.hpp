#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus::Panel {
// Intentional borrowed provider composition; original layout/inheritance and
// ordinary return declaration unresolved. Registry and metadata must stay live.
class AlertBook {
public:
  explicit AlertBook(Core::Portable::Component &parameters)
      : parameters_(parameters) {}
  void setParamString(const char *text, int tag);

private:
  Core::Portable::Component &parameters_;
};
} // namespace Presonus::Panel
