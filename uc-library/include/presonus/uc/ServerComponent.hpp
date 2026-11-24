#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus::UC {
class MessageAttributes;
// Intentional source port: actual pinned CCL base, not original ARM layout.
class ServerComponent : public Core::Portable::Component {
public:
  using Core::Portable::Component::Component;
  ~ServerComponent() override;
  // Portable default hook. Exact original declaration remains unresolved.
  void notify(const MessageAttributes &);
};
} // namespace Presonus::UC
