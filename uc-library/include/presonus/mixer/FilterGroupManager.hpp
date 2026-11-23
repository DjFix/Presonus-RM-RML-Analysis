#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus::UC {
class MessageAttributes;
}
namespace Presonus::Mixer {
// Intentional CCL 5.0.0 source port. Original ARM layout and complete virtual
// interface are unresolved.
class FilterGroupManager : public Core::Portable::Component {
public:
  explicit FilterGroupManager(const char *name);
  ~FilterGroupManager() override;
  // Provisional void return; real CCL children own authoritative names/params.
  void resetChannelNames();
  // Provisional void return. Reorders only within the stable CCL child tree.
  void notify(const UC::MessageAttributes &message);
};
} // namespace Presonus::Mixer
