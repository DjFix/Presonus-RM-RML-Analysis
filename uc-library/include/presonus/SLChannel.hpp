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
