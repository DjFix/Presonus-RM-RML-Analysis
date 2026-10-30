#include "presonus/uc/event_factory.hpp"

namespace Presonus::UC {
// Unchanged application destructor body, split from owned Queue lifetime so
// this real IntrusiveLink-based key function has an independent source owner.
EventItem::~EventItem() {}
} // namespace Presonus::UC
