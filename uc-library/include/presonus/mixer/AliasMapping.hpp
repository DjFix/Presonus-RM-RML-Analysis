#pragma once
#include "presonus/mixer/ControlMapping.hpp"
namespace Core::Portable {
class AliasParam;
class Component;
} // namespace Core::Portable
namespace Presonus {
class MixerClientComponentBase;
}
namespace Presonus::Mixer {
// Portable source port. Native offset 0x28 stores the borrowed alias pointer;
// original base/vtable/layout and retention beyond construction remain unknown.
class AliasMapping : public ControlMapping {
public:
  AliasMapping(Core::Portable::AliasParam *, Core::Portable::Parameter *,
               const char *);
  Core::Portable::AliasParam *alias() const { return alias_; }
  // Independent borrowed association with the mixer's real CCL lookup root.
  void bindMixerRoot(MixerClientComponentBase &mixer,
                     Core::Portable::Component &root);
  // Source-port void choice. The original ordinary return is unresolved.
  void connect(MixerClientComponentBase *mixer);

private:
  Core::Portable::AliasParam *alias_;
  MixerClientComponentBase *mixer_ = nullptr;
  Core::Portable::Component *root_ = nullptr;
};
} // namespace Presonus::Mixer
