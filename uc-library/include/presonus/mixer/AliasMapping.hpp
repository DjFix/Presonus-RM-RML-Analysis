#pragma once
#include "presonus/mixer/ControlMapping.hpp"
namespace Core::Portable {
class AliasParam;
}
namespace Presonus::Mixer {
// Portable source port. Native offset 0x28 stores the borrowed alias pointer;
// original base/vtable/layout and retention beyond construction remain unknown.
class AliasMapping : public ControlMapping {
public:
  AliasMapping(Core::Portable::AliasParam *, Core::Portable::Parameter *,
               const char *);
  Core::Portable::AliasParam *alias() const { return alias_; }

private:
  Core::Portable::AliasParam *alias_;
};
} // namespace Presonus::Mixer
