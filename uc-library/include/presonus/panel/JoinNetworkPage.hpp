#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus::Panel {
// Independent source-port composition. Borrowed tree must remain live and
// contain a real StringParam tag 8. Original bases/layout and void return
// declaration remain unresolved; this constructor is portable setup only.
class JoinNetworkPage {
public:
  explicit JoinNetworkPage(Core::Portable::Component &tree) : tree_(tree) {}
  void recall();

private:
  Core::Portable::Component &tree_;
};
} // namespace Presonus::Panel
