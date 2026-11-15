#pragma once
#include "core/public/corebitset.h"
#include "presonus/surface/MixerPageComponent.hpp"
namespace Presonus::Surface {
// Portable source model. Independent default initialization does not recover
// the original (const char*, int) constructor, inheritance or ARM object
// layout. Ordinary void returns below are chosen source declarations, still
// pending.
class TBRoutingPageComponent : public MixerPageComponent {
public:
  TBRoutingPageComponent() = default;
  ~TBRoutingPageComponent() override;
  void connectChannel(const Core::Portable::Component *, int, bool);
  void disconnectMappables();
  // Independent setup. ParamList owns parameters; vector borrows them.
  void retainMappable(Core::Portable::Parameter *p) { mappables_.add(p); }
  Core::Portable::AliasParam &addRoutingAlias(int tag, const char *name) {
    auto *p = Core::Portable::AliasParam::cast(paramList.addAlias(tag, name));
    retainMappable(p);
    return *p;
  }

private:
  Core::Vector<Core::Portable::Parameter *> mappables_;
  Core::BitSet assignmentBits_{16};
};
} // namespace Presonus::Surface
