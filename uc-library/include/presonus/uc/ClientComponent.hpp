#pragma once
#include "core/portable/corecomponent.h"

namespace Presonus::UC {
class MessageAttributes;

class ClientComponent : public Core::Portable::Component {
public:
  // Source-port construction uses the pinned provider's lifecycle.
  using Core::Portable::Component::Component;

  // The native slot is established. The portable return spelling and vtable
  // layout carry no original declaration or ABI claim.
  virtual void notify(const MessageAttributes &);
};
} // namespace Presonus::UC
