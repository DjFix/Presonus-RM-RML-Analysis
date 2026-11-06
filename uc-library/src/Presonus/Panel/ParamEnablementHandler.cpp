#include "presonus/panel/ParamEnablementHandler.hpp"
namespace Presonus::Panel {
static_assert(Core::Portable::Parameter::kChanged == 3);
void ParamEnablementHandler::paramChanged(Core::Portable::Parameter *,
                                          int msg) {
  if (msg == Core::Portable::Parameter::kChanged)
    changed();
}
void ParamEnablementHandler::addDependency(Core::Portable::Parameter *p,
                                           bool observe) {
  dependencies.add(p);
  if (observe)
    p->addObserver(this);
}
void ParamEnablementHandler::addTarget(Core::Portable::Parameter *p) {
  targets.add(p);
}
void ParamEnablementHandler::changed() {
  bool enabled = true;
  const int dependencyCount = dependencies.count();
  for (int i = 0; i < dependencyCount; ++i)
    if (dependencies[i]->getValue() == 0.f) {
      enabled = false;
      break;
    }
  const int targetCount = targets.count();
  for (int i = 0; i < targetCount; ++i)
    targets[i]->enable(enabled);
}
ParamEnablementHandler::~ParamEnablementHandler() {
  const int count = dependencies.count();
  for (int i = 0; i < count; ++i)
    dependencies[i]->removeObserver(this);
  // Reverse member destruction releases dependency storage before targets.
}
} // namespace Presonus::Panel
