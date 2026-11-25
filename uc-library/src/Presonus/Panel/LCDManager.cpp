#include "presonus/panel/LCDManager.hpp"

DEFINE_SINGLETON(Presonus::Panel::LCDManager)

namespace Presonus::Panel {
LCDManager::LCDManager() = default;
LCDManager::~LCDManager() = default;

void LCDManager::setDelegate(ILCDDelegate *delegate) { delegate_ = delegate; }

void LCDManager::doIdle() {
  if (delegate_)
    delegate_->doIdle();
}

Book *LCDManager::getDefaultBook() const {
  return delegate_ ? delegate_->getDefaultBook() : nullptr;
}

Core::Portable::Parameter *
LCDManager::lookupElementParameter(const char *name) const {
  return delegate_ ? delegate_->lookupElementParameter(name) : nullptr;
}
} // namespace Presonus::Panel
