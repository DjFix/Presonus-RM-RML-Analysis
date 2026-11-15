#include "presonus/surface/PageHeaderComponent.hpp"
namespace Presonus::Surface {
void PageHeaderComponent::disconnectMappables() {
  MappablePageComponent::disconnectMappables();
  if (label_)
    label_->fromString("", false);
}
} // namespace Presonus::Surface
