#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus::Surface {
// Actual pinned provider inheritance is an intentional source port, not proof
// of original complete inheritance/layout or ordinary return declarations.
class ChannelInfoPageComponent : public Core::Portable::Component {
public:
  using Component::Component;
  ~ChannelInfoPageComponent() override;
  // Independent source-port binding: vector owns storage, never pointees.
  Core::Vector<Core::Portable::AliasParam *> &sourcePortAliases() {
    return aliases_;
  }
  void handleLocalSourceSelect(float value);
  void handleExternalSourceSelect();

private:
  Core::Vector<Core::Portable::AliasParam *> aliases_;
};
} // namespace Presonus::Surface
