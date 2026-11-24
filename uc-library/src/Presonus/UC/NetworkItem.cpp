#include "presonus/uc/NetworkItem.hpp"

namespace Presonus::UC {
NetworkItem::~NetworkItem() = default;

void *NetworkItem::getComponent() const { return component_; }
} // namespace Presonus::UC
