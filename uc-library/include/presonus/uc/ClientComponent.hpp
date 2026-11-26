#pragma once
#include "core/portable/corecomponent.h"

namespace Presonus::UC {
class MessageAttributes;
class ClientRootComponent;

class ClientComponent : public Core::Portable::Component {
public:
  ClientComponent(const char *name = "");
  void *castTo(int typeId) override;
  virtual ClientRootComponent *getRoot();
  void paramChanged(Core::Portable::Parameter *, int) override;

  // The native slot is established. The portable return spelling and vtable
  // layout carry no original declaration or ABI claim.
  virtual void notify(const MessageAttributes &);
};
} // namespace Presonus::UC
