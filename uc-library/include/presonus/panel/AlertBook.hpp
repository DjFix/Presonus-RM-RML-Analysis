#pragma once
#include "core/portable/corecomponent.h"
#include <cstdint>
namespace Presonus::Panel {
class Page;
// Independent portable state: Page is borrowed and never dereferenced here.
struct AlertBookState {
  int mode = 0;
  Page *page = nullptr;
  Core::Portable::Parameter *selection = nullptr;
  std::int64_t startedMilliseconds = 0;
};
// Intentional borrowed provider composition; original layout/inheritance and
// ordinary return declaration unresolved. Registry and metadata must stay live.
class AlertBook {
public:
  explicit AlertBook(Core::Portable::Component &parameters)
      : parameters_(parameters) {}
  void setParamString(const char *text, int tag);
  void setup(Page *, Core::Portable::Parameter *, const char *, const char *,
             const char *, int);
  void deactivated();
  const AlertBookState &portableAlertState() const { return state_; }
  // Real borrowed CCL observer composition, no original inheritance claim.
  // Deactivate before releasing the provider/observed parameter.

private:
  Core::Portable::Component &parameters_;
  AlertBookState state_;
};
} // namespace Presonus::Panel
