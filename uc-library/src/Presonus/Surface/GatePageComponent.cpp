#include "presonus/surface/GatePageComponent.hpp"
namespace Presonus::Surface {
void GatePageComponent::initKeyListen() {
  auto *source = findParameter("ch_key_listen");
  if (!source)
    return;
  if (auto *destination = findParameter("key_listen"))
    destination->setValue(source->getValue(), false);
  // Native getOriginal is called once for comparison when previous is present,
  // and again for the final store. Do not hoist or replace it with alias
  // identity.
  if (previousOriginal_ && previousOriginal_ != source->getOriginal())
    previousOriginal_->setValue(0.f, true);
  previousOriginal_ = source->getOriginal();
}

void GatePageComponent::onKeyListen(bool enabled) {
  if (auto *parameter = findParameter("ch_key_listen"))
    parameter->setValue(enabled ? 1.f : 0.f, true);
}
} // namespace Presonus::Surface
