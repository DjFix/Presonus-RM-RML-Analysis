#include "presonus/LinkControl.hpp"
namespace Presonus {
bool LinkControl::isLinked() const {
  auto *p = getParameter();
  return p && p->getValue() != 0.f;
}
bool LinkControl::isRightSideOfLink() const {
  return rightSideParam && rightSideParam->getValue() != 0.f;
}
void LinkControl::setRightSideParam(Core::Portable::Parameter *p) {
  if (p == rightSideParam)
    return;
  if (rightSideParam)
    rightSideParam->removeObserver(this);
  rightSideParam = p;
  if (p)
    p->addObserver(this);
  invalidate();
}
void LinkControl::paramChanged(Core::Portable::Parameter *p, int msg) {
  if (msg == Core::Portable::Parameter::kChanged && p == rightSideParam)
    invalidate();
  if (msg == Core::Portable::Parameter::kDestroyed && p == rightSideParam)
    rightSideParam = nullptr;
  Control::paramChanged(p, msg);
}
void LinkControl::setAttributes(const Core::Portable::Attributes &a) {
  Core::Portable::View::setAttributes(a);
  leftImage = Core::Portable::ViewAttributes::getBitmap(a, "leftImage");
  rightImage = Core::Portable::ViewAttributes::getBitmap(a, "rightImage");
}
} // namespace Presonus
