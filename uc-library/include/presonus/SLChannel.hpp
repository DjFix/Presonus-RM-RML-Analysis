#pragma once

#include "core/portable/corecomponent.h"

namespace Presonus {
// Source-port inheritance and type ID: intentional CCL5 typed-object
// adaptation, not a claim about original ARM layout, private declarations or
// RTTI identity.
class SLChannelBase : public Core::Portable::Component {
public:
  DECLARE_CORE_CLASS(0x534c4342, SLChannelBase, Core::Portable::Component)
  using Core::Portable::Component::Component;
  virtual Core::Portable::Parameter *getSelectionParameter() const;
  // These nullable Parameter returns are intentional source-port declarations.
  // Original ARM bodies return zero without instance access. Their ordinary
  // return declarations/pointee qualifiers and original vtable layout remain
  // unresolved; matching method names do not establish ARM ABI compatibility.
  virtual Core::Portable::Parameter *getLinkParameter() const;
  virtual Core::Portable::Parameter *getColorParameter() const;
  virtual Core::Portable::Parameter *getLinkMasterParameter() const;
  virtual Core::Portable::Parameter *getLinkedSelectionParameter() const;
};

class SLChannel : public SLChannelBase {
public:
  // Independent source-only setup; the initialized parameter is borrowed and
  // must outlive this channel. No original constructor/lifecycle credit.
  SLChannel(const char *name, Core::Portable::Parameter *selection)
      : SLChannelBase(name), selection_(selection) {}
  Core::Portable::Parameter *getSelectionParameter() const override;

private:
  Core::Portable::Parameter *selection_;
};
} // namespace Presonus
