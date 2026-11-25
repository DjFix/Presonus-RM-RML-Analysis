#pragma once
#include "core/portable/corecomponent.h"

namespace Presonus::UC {
class MessageAttributes;

class ClientComponent : public Core::Portable::Component {
public:
  ClientComponent(const char *name = "");
  void *castTo(int typeId) override;

  // The native slot is established. The portable return spelling and vtable
  // layout carry no original declaration or ABI claim.
  virtual void notify(const MessageAttributes &);
};
} // namespace Presonus::UC
