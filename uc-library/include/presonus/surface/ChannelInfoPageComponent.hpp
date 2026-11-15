#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus::Surface {
// Actual pinned provider inheritance is an intentional source port, not proof
// of original complete inheritance/layout or ordinary return declarations.
class ChannelInfoPageComponent : public Core::Portable::Component {
public:
  using Component::Component;
  void handleLocalSourceSelect(float value);
  void handleExternalSourceSelect();
};
} // namespace Presonus::Surface
