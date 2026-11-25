#include "presonus/uc/NetworkItem.hpp"

namespace Presonus::UC {
NetworkItem::NetworkItem(Type type) : type_(type) {}

NetworkItem::~NetworkItem() = default;

void *NetworkItem::getComponent() const { return component_; }
bool NetworkItem::isAccessAcquired() const { return accessObservation_ != 0; }
void NetworkItem::getTitle(Core::CStringBuffer<128> &title) const {
  title.empty().append(description_.applicationName.str());
  if (type_ == static_cast<Type>(1))
    title.append(" ").append(description_.applicationVersion.str());
  title.append(" ")
      .append(description_.hostAddress.str())
      .append(" ")
      .append(description_.hostName.str());
}
} // namespace Presonus::UC
