#include "presonus/StormMixSceneComponent.hpp"
namespace Presonus {
bool StormMixSceneComponent::isStoreOn() const {
  auto *p = getParameterByTag(0);
  return p && p->getValue() > 0.f;
}
void StormMixSceneComponent::setAllMixButtons(bool state) {
  for (int tag = 2; auto *p = getParameterByTag(tag); ++tag)
    p->setValue(state ? 1.f : 0.f, false);
  selectedIndex = UINT32_MAX;
}
void StormMixSceneComponent::enterStoreState(bool state) {
  if (delegate) {
    if (state)
      delegate->enter(*this);
    else
      delegate->leave(*this);
  }
  setAllMixButtons(false);
}
void StormMixSceneComponent::doRecall(unsigned int index) {
  setAllMixButtons(false);
  if (!recallBoundary.recall(index))
    return;
  selectedIndex = index;
  // ARM wraps the unsigned increment before the signed-tag lookup.
  auto *p = getParameterByTag(static_cast<std::int32_t>(index + 1U));
  if (p)
    p->setValue(p->getTag() == 1 ? 0.f : 1.f, false);
}
void StormMixSceneComponent::onIdle() {
  Core::Portable::Component::onIdle();
  if (isStoreOn())
    return;
  const auto count = timerCount;
  auto **items = timers;
  auto **fixtures = fixtureTimers;
  for (unsigned int i = 0; i < count; ++i) {
    if (fixtures) {
      auto *timer = fixtures[i];
      if (timer && timer->executing() && timer->longEnough()) {
        timer->end();
        doRecall(i);
      }
    } else {
      auto *timer = items[i];
      if (timer && timer->isExecuting() && timer->isLongEnoughYet()) {
        (void)timer->endAction();
        doRecall(i);
      }
    }
  }
}
} // namespace Presonus
