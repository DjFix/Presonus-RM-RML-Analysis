#pragma once

#include "core/public/coreproperty.h"
namespace Presonus::Dsp {
// Partial source port for the closed release and default property bodies.
// Original fields, inheritance, class size and hardware behavior are
// unresolved.
class OMAPTargetHandler {
public:
  struct SourcePortConstruction {};
  explicit OMAPTargetHandler(SourcePortConstruction) noexcept {}
  // Exclusive global-new allocation of this trivial port type, exactly once.
  // No destructor/virtual cleanup is observed in the original release body.
  // Ordinary return declaration remains unresolved; portable void is pending.
  void release();
  // The portable void return remains an unresolved original declaration.
  virtual void getProperty(Core::Property &);
};
} // namespace Presonus::Dsp
