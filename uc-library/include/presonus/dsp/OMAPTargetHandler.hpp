#pragma once
namespace Presonus::Dsp {
// Minimal partial source port for the closed release body only. No original
// fields, inheritance, class size, constructor or hardware behavior is claimed.
class OMAPTargetHandler {
public:
  struct SourcePortConstruction {};
  explicit OMAPTargetHandler(SourcePortConstruction) noexcept {}
  // Exclusive global-new allocation of this trivial port type, exactly once.
  // No destructor/virtual cleanup is observed in the original release body.
  // Ordinary return declaration remains unresolved; portable void is pending.
  void release();
};
} // namespace Presonus::Dsp
