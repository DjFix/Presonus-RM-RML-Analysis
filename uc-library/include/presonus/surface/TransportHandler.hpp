#pragma once
#include "core/portable/coreparams.h"
namespace Presonus::Surface {
// Partial portable source port. Real CCL observer/list types replace native
// subobject offsets; original inheritance, layout and ARM ABI are unresolved.
// The omitted paramChanged/castTo implementations remain abstract, not no-ops.
class TransportHandler : public Core::Portable::IParamObserver {
public:
  virtual ~TransportHandler();
  const char *getName() const;
  // void/member is a portable declaration; the ELF does not encode its return.
  // Borrow parameters; caller detaches outstanding external observations before
  // destroying this handler. Native destructor does not unregister them.
  void setAndObserve(Core::Portable::Parameter *&slot,
                     Core::Portable::Parameter *parameter);
  // Independent source-port state, not the original field layout or
  // constructor.
  Core::Portable::ParamList paramList;
};
} // namespace Presonus::Surface
