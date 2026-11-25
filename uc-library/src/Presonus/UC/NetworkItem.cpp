#include "presonus/uc/NetworkItem.hpp"

namespace Presonus::UC {
NetworkItem::~NetworkItem() = default;

void *NetworkItem::getComponent() const { return component_; }
bool NetworkItem::isAccessAcquired() const { return accessObservation_ != 0; }
} // namespace Presonus::UC
