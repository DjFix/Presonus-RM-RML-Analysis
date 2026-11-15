#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus::Surface {
// Actual CCL-backed source-port base; original inheritance/layout unverified.
class GatePageComponent : public Core::Portable::Component {
public:
  // Provisional void return; original ordinary declaration unresolved.
  void onKeyListen(bool enabled);
  // Provisional void return. Uses the real inherited CCL parameter registry.
  void initKeyListen();
  // Independent borrowed source-port state for native +0xc8. Original field
  // name/type/layout and constructor initialization are not established.
  // Previous/source original parameters must outlive every call; no ownership
  // transfer. Supported source is Numeric or Alias with stable Numeric
  // original.
  void setSourcePortPreviousOriginal(Core::Portable::NumericParam *previous) {
    previousOriginal_ = previous;
  }
  Core::Portable::Parameter *getSourcePortPreviousOriginal() const {
    return previousOriginal_;
  }

private:
  Core::Portable::Parameter *previousOriginal_ = nullptr;
};
} // namespace Presonus::Surface
