#include "presonus/panel/LCDManager.hpp"

namespace Presonus::Panel {
void LCDManager::setDelegate(ILCDDelegate *delegate) { delegate_ = delegate; }

Book *LCDManager::getDefaultBook() const {
  return delegate_ ? delegate_->getDefaultBook() : nullptr;
}

Core::Portable::Parameter *
LCDManager::lookupElementParameter(const char *name) const {
  return delegate_ ? delegate_->lookupElementParameter(name) : nullptr;
}
} // namespace Presonus::Panel
